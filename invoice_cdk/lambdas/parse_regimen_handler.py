import os
import json
import base64
import traceback
from http import HTTPStatus
from constantes import Constants
from utils import valida_cors
#from requests_toolbelt.multipart import decoder
from pdf_regimen_parser_pymupdf import RegimenFiscalPyMuPDFParser


headers = Constants.HEADERS.copy()


def handler(event, context):
    print("Event:", event)
    origin = event.get('headers', {}).get('origin')
    headers["Access-Control-Allow-Origin"] = valida_cors(origin)
    try:
        # lazy import to surface import errors immediately
        from requests_toolbelt.multipart import decoder
    except Exception:
        print("Error importing requests_toolbelt:", traceback.format_exc())
        return {
            "statusCode": HTTPStatus.INTERNAL_SERVER_ERROR,
            "headers": headers,
            "body": json.dumps({"message": "Import error: requests_toolbelt not available. Revisar layer."})
        }
    try:
        http_method = event.get('httpMethod')
        if http_method != Constants.POST:
            return {
                Constants.STATUS_CODE: HTTPStatus.METHOD_NOT_ALLOWED,
                Constants.BODY: json.dumps({"error": "Only POST allowed"}),
                Constants.HEADERS_KEY: headers
            }

        content_type = event.get('headers', {}).get('Content-Type') or event.get('headers', {}).get('content-type', '')
        body = event.get('body', '')
        is_b64 = event.get('isBase64Encoded', False)

        # Normalize to bytes
        if is_b64 and body:
            body_bytes = base64.b64decode(body)
        else:
            # If it's raw JSON containing base64
            if 'application/json' in content_type and body:
                data = json.loads(body)
                pdf_b64 = data.get('pdf_base64') or data.get('pdfB64')
                if not pdf_b64:
                    return {
                        Constants.STATUS_CODE: HTTPStatus.BAD_REQUEST,
                        Constants.BODY: json.dumps({"error": "Missing pdf_base64 in JSON body"}),
                        Constants.HEADERS_KEY: headers
                    }
                body_bytes = base64.b64decode(pdf_b64)
            else:
                # Treat body as binary string; encode using latin1 to preserve bytes
                body_bytes = body.encode('latin1') if isinstance(body, str) else body

        # Extract PDF bytes from multipart if needed
        pdf_bytes = None
        if 'multipart/form-data' in content_type:
            multipart_data = decoder.MultipartDecoder(body_bytes, content_type)
            for part in multipart_data.parts:
                cd = part.headers.get(b'Content-Disposition', b'').decode()
                # look for common field names or filename
                if 'name="csf"' in cd:
                    pdf_bytes = part.content
                    break
            if pdf_bytes is None:
                # fallback: take first part
                if multipart_data.parts:
                    pdf_bytes = multipart_data.parts[0].content
        elif 'application/pdf' in content_type or content_type == '':
            pdf_bytes = body_bytes
        else:
            # fallback: assume body_bytes is the pdf
            pdf_bytes = body_bytes

        if not pdf_bytes:
            return {
                Constants.STATUS_CODE: HTTPStatus.BAD_REQUEST,
                Constants.BODY: json.dumps({"error": "PDF not found in request"}),
                Constants.HEADERS_KEY: headers
            }

        parser = RegimenFiscalPyMuPDFParser()
        datos_csf = parser.extract_from_bytes(pdf_bytes)

        return {
            Constants.STATUS_CODE: HTTPStatus.OK,
            Constants.BODY: json.dumps({"csf": datos_csf}),
            Constants.HEADERS_KEY: headers
        }

    except Exception as e:
        traceback.print_exc()
        return {
            Constants.STATUS_CODE: HTTPStatus.INTERNAL_SERVER_ERROR,
            Constants.BODY: json.dumps({"error": str(e)}),
            Constants.HEADERS_KEY: headers
        }
