from aws_cdk import (
    Duration,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
    aws_cognito as cognito,
    aws_iam as iam,
)
from constructs import Construct
APPLICATION_JSON = "application/json"
class CertificateApiGateway(Construct):
    def __init__(self, scope: Construct, id: str, lambdas: dict, user_pool: cognito.UserPool):
        super().__init__(scope, id)
        self.certificate_lambda: _lambda.Function = lambdas.get("certificate_lambda")
        self.sucursal_lambda: _lambda.Function = lambdas.get("sucursal_lambda")
        self.datos_factura_lambda: _lambda.Function = lambdas.get("datos_factura_lambda")
        self.tapetes_lambda: _lambda.Function = lambdas.get("tapetes_lambda")
        self.folio_lambda: _lambda.Function = lambdas.get("folio_lambda")
        self.genera_factura_lambda: _lambda.Function = lambdas.get("genera_factura_lambda")
        self.receptor_lambda: _lambda.Function = lambdas.get("receptor_lambda")
        self.maneja_certificado_lambda: _lambda.Function = lambdas.get("maneja_certificado_lambda")
        self.timbres_consumo_lambda: _lambda.Function = lambdas.get("timbres_consumo_lambda")
        self.parsea_pdf_regimen_lambda: _lambda.Function = lambdas.get("parsea_pdf_regimen_lambda")
        self.environment_handler_lambda: _lambda.Function = lambdas.get("environment_handler_lambda")

        # Create a single RestApi instance
        api = apigw.RestApi(
            self,
            "InvoiceAPI",
            rest_api_name="Invoice API",
            description="This service manages certificates and branches.",
            default_cors_preflight_options={
                "allow_origins": ['https://factura.farzin.com.mx', 'http://localhost:4200'],
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
                "allow_origins": ['https://factura.farzin.com.mx', 'http://localhost:4200'],
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
        
        #Folio resource
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

        # Integrations
        certificate_integration = apigw.LambdaIntegration(
            self.certificate_lambda,
            request_templates={APPLICATION_JSON: '{ "statusCode": "200" }'}
        )

        sucursal_integration = apigw.LambdaIntegration(
            self.sucursal_lambda,
            request_templates={APPLICATION_JSON: '{ "statusCode": "200" }'}
        )

        datos_factura_integration = apigw.LambdaIntegration(
            self.datos_factura_lambda,
            request_templates={APPLICATION_JSON: '{ "statusCode": "200" }'}
        )

        tapetes_integration = apigw.LambdaIntegration(
            self.tapetes_lambda,
            request_templates={APPLICATION_JSON: '{ "statusCode": "200" }'}
        )   

        folio_integration = apigw.LambdaIntegration(
            self.folio_lambda,
            request_templates={APPLICATION_JSON: '{ "statusCode": "200" }'}
        )

        genera_factura_integration = apigw.LambdaIntegration(
            self.genera_factura_lambda,
            request_templates={APPLICATION_JSON: '{ "statusCode": "200" }'}
        )

        receptor_integration = apigw.LambdaIntegration(
            self.receptor_lambda,
            request_templates={APPLICATION_JSON: '{ "statusCode": "200" }'}
        )

        maneja_certificado_integration = apigw.LambdaIntegration(
            self.maneja_certificado_lambda,
            request_templates={APPLICATION_JSON: '{ "statusCode": "200" }'}
        )

        consumo_timbres_integration = apigw.LambdaIntegration(
            self.timbres_consumo_lambda,
            request_templates={APPLICATION_JSON: '{ "statusCode": "200" }'}
        )

        parsea_pdf_regimen_integration = apigw.LambdaIntegration(
            self.parsea_pdf_regimen_lambda,
            request_templates={APPLICATION_JSON: '{ "statusCode": "200" }'}
        )

        environment_integration = apigw.LambdaIntegration(
            self.environment_handler_lambda,
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
