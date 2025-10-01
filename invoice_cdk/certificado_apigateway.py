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
    def __init__(self, scope: Construct, id: str, certificate_lambda: _lambda.Function, 
                 sucursal_lambda: _lambda.Function, 
                 datos_factura_lambda: _lambda.Function, 
                 tapetes_lambda: _lambda.Function, 
                 folio_lambda: _lambda.Function, 
                 genera_factura_lambda: _lambda.Function,
                 receptor_lambda: _lambda.Function,
                 maneja_certificado_lambda: _lambda.Function,
                 timbres_consumo_lambda: _lambda.Function,
                 parsea_pdf_regimen_lambda: _lambda.Function,
                 user_pool: cognito.IUserPool):
        super().__init__(scope, id)
       
       
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
        
        #user_pool = cognito.UserPool.from_user_pool_id(self, "ImportedUserPool", user_pool_id)
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

        # Integrations
        certificate_integration = apigw.LambdaIntegration(
            certificate_lambda,
            request_templates={APPLICATION_JSON: '{ "statusCode": "200" }'}
        )

        sucursal_integration = apigw.LambdaIntegration(
            sucursal_lambda,
            request_templates={APPLICATION_JSON: '{ "statusCode": "200" }'}
        )

        datos_factura_integration = apigw.LambdaIntegration(
            datos_factura_lambda,
            request_templates={APPLICATION_JSON: '{ "statusCode": "200" }'}
        )

        tapetes_integration = apigw.LambdaIntegration(
            tapetes_lambda,
            request_templates={APPLICATION_JSON: '{ "statusCode": "200" }'}
        )   

        folio_integration = apigw.LambdaIntegration(
            folio_lambda,
            request_templates={APPLICATION_JSON: '{ "statusCode": "200" }'}
        )

        genera_factura_integration = apigw.LambdaIntegration(
            genera_factura_lambda,
            request_templates={APPLICATION_JSON: '{ "statusCode": "200" }'}
        )

        receptor_integration = apigw.LambdaIntegration(
            receptor_lambda,
            request_templates={APPLICATION_JSON: '{ "statusCode": "200" }'}
        )

        maneja_certificado_integration = apigw.LambdaIntegration(
            maneja_certificado_lambda,
            request_templates={APPLICATION_JSON: '{ "statusCode": "200" }'}
        )

        consumo_timbres_integration = apigw.LambdaIntegration(
            timbres_consumo_lambda,
            request_templates={APPLICATION_JSON: '{ "statusCode": "200" }'}
        )

        parsea_pdf_regimen_integration = apigw.LambdaIntegration(
            parsea_pdf_regimen_lambda,
            request_templates={APPLICATION_JSON: '{ "statusCode": "200" }'}
        )

        # Certificate methods (CON CUSTOM AUTHORIZER)
        certificates_resource.add_method("POST", certificate_integration,)
        certificates_resource.add_method("GET", certificate_integration, authorization_type=apigw.AuthorizationType.COGNITO, authorizer=authorizer)
        certificate_id_resource.add_method("GET", certificate_integration)
        certificate_id_resource.add_method("PUT", certificate_integration)
        certificate_id_resource.add_method("DELETE", certificate_integration)#, authorizer=authorizer)

        # Sucursal methods (CON CUSTOM AUTHORIZER)
        sucursales_resource.add_method("POST", sucursal_integration)
        sucursal_id_resource.add_method("GET", sucursal_integration)
        sucursal_id_resource.add_method("PUT", sucursal_integration)#, authorizer=authorizer)
        sucursal_id_resource.add_method("DELETE", sucursal_integration)#, authorizer=authorizer)

        # Datos Factura methods, no lleva authorizer
        datos_factura.add_method("GET", datos_factura_integration)#, authorizer=datos_factura_authorizer, authorization_type=apigw.AuthorizationType.COGNITO)

        #Datos Tapetes methods, obtiene el ticket de venta, no lleva authorizer
        tapetes_id_resource.add_method("GET", tapetes_integration)

        #Datos Folio methods 
        folio_resource.add_method("POST", folio_integration)

        #Datos Genera Factura methods, no lleva authorizer
        genera_factura.add_method("POST", genera_factura_integration)

        #Datos Receptor methods, no lleva authorizer
        receptor_resource.add_method("POST", receptor_integration)
        receptor_id_resource.add_method("GET", receptor_integration)
        receptor_id_resource.add_method("PUT", receptor_integration)

        # Maneja Certificado methods
        maneja_certificado_resource.add_method("POST", maneja_certificado_integration)
        maneja_certificado_id_resource.add_method("DELETE", maneja_certificado_integration)

        # Consumo Timbres methods
        timbre_usuario_resource.add_method("GET", consumo_timbres_integration)

        # Parsea PDF Regimen methods
        parsea_pdf_regimen_resource.add_method("POST", parsea_pdf_regimen_integration)
