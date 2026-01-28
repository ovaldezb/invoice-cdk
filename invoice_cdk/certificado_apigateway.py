from aws_cdk import (
    Duration,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
    aws_cognito as cognito,
    aws_iam as iam,
)
from constructs import Construct
from dotenv import load_dotenv  # Agregar import
import os

load_dotenv()  # Cargar variables de entorno desde el archivo .env
APPLICATION_JSON = "application/json"
class CertificateApiGateway(Construct):
    def __init__(self, scope: Construct, id: str,  alias: dict, user_pool: cognito.UserPool):
        super().__init__(scope, id)
        
        self.alias_certificate = alias.get("certificate_alias")
        self.alias_sucursal = alias.get("sucursal_alias")
        self.alias_datos_factura = alias.get("datos_factura_alias")
        self.alias_tapetes = alias.get("tapetes_alias")
        self.alias_folio = alias.get("folio_alias")
        self.alias_genera_factura = alias.get("genera_factura_alias")
        self.alias_receptor = alias.get("receptor_alias")
        self.alias_maneja_certificado = alias.get("maneja_certificado_alias")
        self.alias_timbres_consumo = alias.get("timbres_consumo_alias")
        self.alias_parsea_pdf_regimen = alias.get("parsea_pdf_regimen_alias")
        self.alias_environment_handler = alias.get("environment_handler_alias")
        self.alias_bitacora = alias.get("bitacora_alias")
        self.alias_mercado_pago = alias.get("mercado_pago_alias")
        self.alias_mercado_pago_webhook = alias.get("mercado_pago_webhook_alias")
        self.alias_get_payments = alias.get("get_payments_alias")
        self.alias_payment_config = alias.get("payment_config_alias")
        self.alias_get_invoice_count = alias.get("get_invoice_count_alias")
        self.alias_timbrado_service = alias.get("timbrado_service_alias")
        self.alias_openpay = alias.get("openpay_alias")

        server = os.getenv("CORS_OPTION")
        print("CORS OPTION:", server)
        # Create a single RestApi instance
        api = apigw.RestApi(
            self,
            "InvoiceAPI",
            rest_api_name="Invoice API",
            description="This service manages certificates and branches.",
            default_cors_preflight_options={
                "allow_origins": [server, 'http://localhost:4200'],
                "allow_methods": ['OPTIONS','GET','POST','PUT','DELETE'],
                "allow_headers": ["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key", "X-Amz-Security-Token"],
                "allow_credentials": True
            },
            binary_media_types=[
                "application/x-x509-ca-cert",
                "application/x-iwork-keynote-sffkey",
                "multipart/form-data"
            ],
        )

        datos_factura_apigw=apigw.RestApi(
            self,
            "DatosFacturaAPI",
            rest_api_name="DatosFactura Invoice API",
            description="This service manages Datos Factura.",
            default_cors_preflight_options={
                "allow_origins": [server, 'http://localhost:4200'],
                "allow_methods": ['OPTIONS','GET','POST','PUT','DELETE'],
                "allow_headers": ["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key", "X-Amz-Security-Token"],
                "allow_credentials": True
            }
        )

        # Create authorizer (preferir custom authorizer si está disponible)
        
        authorizer = apigw.CognitoUserPoolsAuthorizer(
            self,
            "CognitoAuthorizer",
            cognito_user_pools=[user_pool],
            identity_source="method.request.header.Authorization",
            results_cache_ttl=Duration.minutes(5)
        )
        
        # Certificates resources
        certificates_resource = api.root.add_resource("certificados")
        certificate_id_resource = certificates_resource.add_resource("{id}")

        # Sucursales resources
        sucursales_resource = api.root.add_resource("sucursales")
        sucursal_id_resource = sucursales_resource.add_resource("{id}")

        # Datos Factura resources
        datos_factura = datos_factura_apigw.root.add_resource("datosfactura")

        #Tapetes resource
        tapetes_resource = api.root.add_resource("tapetes")
        tapetes_id_resource = tapetes_resource.add_resource("{ticket}")

        #Folio resource
        folio_resource = api.root.add_resource("folio")
        folio_sucursal_resource = folio_resource.add_resource("{sucursal}")
        
        #Factura resource
        genera_factura = api.root.add_resource("factura")

        # Receptor resource
        receptor_resource = api.root.add_resource("receptor")
        receptor_id_resource = receptor_resource.add_resource("{id_receptor}")

        #Maneja Certificado resource
        maneja_certificado_resource = api.root.add_resource("maneja-certificado")
        maneja_certificado_id_resource = maneja_certificado_resource.add_resource("{id}")

        # Consumo Timbres resource
        timbres_consumo_resource = api.root.add_resource("timbres")
        timbre_usuario_resource = timbres_consumo_resource.add_resource("{usuario}")

        # Parsea PDF Regimen resource
        parsea_pdf_regimen_resource = api.root.add_resource("parsea-pdf")

        # Environment resource
        environment_resource = api.root.add_resource("environment")

        # Bitacora resource
        bitacora_resource = api.root.add_resource("bitacora")

        # Mercado Pago resource
        mercado_pago_resource = api.root.add_resource("mercado-pago")
        mp_create_preference_resource = mercado_pago_resource.add_resource("create-preference")
        mp_webhook_resource = mercado_pago_resource.add_resource("webhook")
        mp_payments_resource = mercado_pago_resource.add_resource("payments")
        mp_config_resource = mercado_pago_resource.add_resource("configuration")

        # Invoices resource
        invoices_resource = api.root.add_resource("invoices")
        invoice_count_resource = invoices_resource.add_resource("count")

        # OpenPay resource
        openpay_resource = api.root.add_resource("openpay")
        openpay_checkout_resource = openpay_resource.add_resource("create-checkout")
        openpay_webhook_resource = openpay_resource.add_resource("webhook")

        # Integrations
        certificate_integration = apigw.LambdaIntegration(
            self.alias_certificate,
            request_templates={APPLICATION_JSON: '{ "statusCode": "200" }'},
        )

        sucursal_integration = apigw.LambdaIntegration(
            self.alias_sucursal,
            request_templates={APPLICATION_JSON: '{ "statusCode": "200" }'}
        )

        datos_factura_integration = apigw.LambdaIntegration(
            self.alias_datos_factura,
            request_templates={APPLICATION_JSON: '{ "statusCode": "200" }'}
        )

        tapetes_integration = apigw.LambdaIntegration(
            self.alias_tapetes,
            request_templates={APPLICATION_JSON: '{ "statusCode": "200" }'}
        )   

        folio_integration = apigw.LambdaIntegration(
            self.alias_folio,
            request_templates={APPLICATION_JSON: '{ "statusCode": "200" }'}
        )

        genera_factura_integration = apigw.LambdaIntegration(
            self.alias_genera_factura,
            request_templates={APPLICATION_JSON: '{ "statusCode": "200" }'}
        )

        receptor_integration = apigw.LambdaIntegration(
            self.alias_receptor,
            request_templates={APPLICATION_JSON: '{ "statusCode": "200" }'}
        )

        maneja_certificado_integration = apigw.LambdaIntegration(
            self.alias_maneja_certificado,
            request_templates={APPLICATION_JSON: '{ "statusCode": "200" }'}
        )

        consumo_timbres_integration = apigw.LambdaIntegration(
            self.alias_timbres_consumo,
            request_templates={APPLICATION_JSON: '{ "statusCode": "200" }'}
        )

        parsea_pdf_regimen_integration = apigw.LambdaIntegration(
            self.alias_parsea_pdf_regimen,
            request_templates={APPLICATION_JSON: '{ "statusCode": "200" }'}
        )

        environment_integration = apigw.LambdaIntegration(
            self.alias_environment_handler,
            request_templates={APPLICATION_JSON: '{ "statusCode": "200" }'}
        )
        bitacora_integration = apigw.LambdaIntegration(
            self.alias_bitacora,
            request_templates={APPLICATION_JSON: '{ "statusCode": "200" }'}
        )
        
        mercado_pago_integration = apigw.LambdaIntegration(
            self.alias_mercado_pago,
            request_templates={APPLICATION_JSON: '{ "statusCode": "200" }'}
        )

        mercado_pago_webhook_integration = apigw.LambdaIntegration(
            self.alias_mercado_pago_webhook,
            request_templates={APPLICATION_JSON: '{ "statusCode": "200" }'}
        )

        get_payments_integration = apigw.LambdaIntegration(
            self.alias_get_payments,
            request_templates={APPLICATION_JSON: '{ "statusCode": "200" }'}
        )

        payment_config_integration = apigw.LambdaIntegration(
            self.alias_payment_config,
            request_templates={APPLICATION_JSON: '{ "statusCode": "200" }'}
        )

        get_invoice_count_integration = apigw.LambdaIntegration(
            self.alias_get_invoice_count,
            request_templates={APPLICATION_JSON: '{ "statusCode": "200" }'}
        )

        openpay_integration = apigw.LambdaIntegration(
            self.alias_openpay,
            request_templates={APPLICATION_JSON: '{ "statusCode": "200" }'}
        )

        # Certificate methods (CON CUSTOM AUTHORIZER)
        certificates_resource.add_method("POST", certificate_integration,authorizer=authorizer, authorization_type=apigw.AuthorizationType.COGNITO)
        certificates_resource.add_method("GET", certificate_integration,authorizer=authorizer, authorization_type=apigw.AuthorizationType.COGNITO)
        certificate_id_resource.add_method("GET", certificate_integration,authorizer=authorizer, authorization_type=apigw.AuthorizationType.COGNITO)
        certificate_id_resource.add_method("PUT", certificate_integration,authorizer=authorizer, authorization_type=apigw.AuthorizationType.COGNITO)
        certificate_id_resource.add_method("DELETE", certificate_integration,authorizer=authorizer, authorization_type=apigw.AuthorizationType.COGNITO)

        # Sucursal methods (CON CUSTOM AUTHORIZER)
        sucursales_resource.add_method("POST", sucursal_integration,authorizer=authorizer, authorization_type=apigw.AuthorizationType.COGNITO)
        sucursal_id_resource.add_method("GET", sucursal_integration,authorizer=authorizer, authorization_type=apigw.AuthorizationType.COGNITO)
        sucursal_id_resource.add_method("PUT", sucursal_integration,authorizer=authorizer, authorization_type=apigw.AuthorizationType.COGNITO)
        sucursal_id_resource.add_method("DELETE", sucursal_integration,authorizer=authorizer, authorization_type=apigw.AuthorizationType.COGNITO)

        # Datos Factura methods, no lleva authorizer
        datos_factura.add_method("GET", datos_factura_integration)

        #Datos Tapetes methods, obtiene el ticket de venta, no lleva authorizer
        tapetes_id_resource.add_method("GET", tapetes_integration)

        #Datos Folio methods 
        folio_resource.add_method("POST", folio_integration)
        folio_resource.add_method("PUT", folio_integration)
        folio_sucursal_resource.add_method("GET", folio_integration)

        #Datos Genera Factura methods, no lleva authorizer
        genera_factura.add_method("POST", genera_factura_integration)
        genera_factura.add_method("PUT", genera_factura_integration)

        #Datos Receptor methods, no lleva authorizer
        receptor_resource.add_method("POST", receptor_integration)
        receptor_id_resource.add_method("GET", receptor_integration)
        receptor_id_resource.add_method("PUT", receptor_integration)

        # Maneja Certificado methods
        maneja_certificado_resource.add_method("POST", maneja_certificado_integration,authorizer=authorizer, authorization_type=apigw.AuthorizationType.COGNITO)
        maneja_certificado_resource.add_method("PUT", maneja_certificado_integration,authorizer=authorizer, authorization_type=apigw.AuthorizationType.COGNITO)
        maneja_certificado_id_resource.add_method("DELETE", maneja_certificado_integration,authorizer=authorizer, authorization_type=apigw.AuthorizationType.COGNITO)


        # Consumo Timbres methods
        timbre_usuario_resource.add_method("GET", consumo_timbres_integration,authorizer=authorizer, authorization_type=apigw.AuthorizationType.COGNITO)

        # Parsea PDF Regimen methods
        parsea_pdf_regimen_resource.add_method("POST", parsea_pdf_regimen_integration)

        # Environment methods
        environment_resource.add_method("GET", environment_integration)

        # Bitacora methods
        bitacora_resource.add_method("GET", bitacora_integration, authorizer=authorizer, authorization_type=apigw.AuthorizationType.COGNITO)

        # Mercado Pago methods (protected)
        mp_create_preference_resource.add_method("POST", mercado_pago_integration, authorizer=authorizer, authorization_type=apigw.AuthorizationType.COGNITO)
        
        # Mercado Pago Webhook (PUBLIC)
        mp_webhook_resource.add_method("POST", mercado_pago_webhook_integration)

        # Mercado Pago Payments (Protected)
        mp_payments_resource.add_method("GET", get_payments_integration, authorizer=authorizer, authorization_type=apigw.AuthorizationType.COGNITO)

        # Mercado Pago Configuration (Protected)
        mp_config_resource.add_method("GET", payment_config_integration, authorizer=authorizer, authorization_type=apigw.AuthorizationType.COGNITO)
        mp_config_resource.add_method("POST", payment_config_integration, authorizer=authorizer, authorization_type=apigw.AuthorizationType.COGNITO)
        mp_config_resource.add_method("DELETE", payment_config_integration, authorizer=authorizer, authorization_type=apigw.AuthorizationType.COGNITO)
        # Invoice Count method (Protected)
        invoice_count_resource.add_method("GET", get_invoice_count_integration, authorizer=authorizer, authorization_type=apigw.AuthorizationType.COGNITO)

        # OpenPay methods
        openpay_checkout_resource.add_method("POST", openpay_integration, authorizer=authorizer, authorization_type=apigw.AuthorizationType.COGNITO)
        openpay_webhook_resource.add_method("POST", openpay_integration) # Public

        # Timbrado Service resource
        timbrado_service_resource = api.root.add_resource("timbrado-service")
        
        timbrado_service_integration = apigw.LambdaIntegration(
            self.alias_timbrado_service,
            request_templates={APPLICATION_JSON: '{ "statusCode": "200" }'}
        )
        
        # Protected POST method
        timbrado_service_resource.add_method("POST", timbrado_service_integration, authorizer=authorizer, authorization_type=apigw.AuthorizationType.COGNITO)
