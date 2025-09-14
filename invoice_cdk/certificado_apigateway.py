from aws_cdk import (
    Duration,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
    aws_cognito as cognito
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
                 agrega_certificado_lambda: _lambda.Function,
                 timbres_consumo_lambda: _lambda.Function,
                 custom_authorizer_lambda: _lambda.Function = None):
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
            ]
        )

        # Create authorizer (preferir custom authorizer si está disponible)
        authorizer = apigw.TokenAuthorizer(
            self,
            "CustomTokenAuthorizer",
            handler=custom_authorizer_lambda,
            authorizer_name="CustomInvoiceAuthorizer"
        )

        # Certificates resources
        certificates_resource = api.root.add_resource("certificados")
        certificate_id_resource = certificates_resource.add_resource("{id}")

        # Sucursales resources
        sucursales_resource = api.root.add_resource("sucursales")
        sucursal_id_resource = sucursales_resource.add_resource("{id}")

        # Datos Factura resources
        datos_factura = api.root.add_resource("datosfactura")

        #Tapetes resource
        tapetes_resource = api.root.add_resource("tapetes")
        tapetes_id_resource = tapetes_resource.add_resource("{ticket}")

        #Folio resource
        folio_resource = api.root.add_resource("folio")
        folio_id_resource = folio_resource.add_resource("{sucursal}")

        #Folio resource
        genera_factura = api.root.add_resource("factura")

        # Receptor resource
        receptor_resource = api.root.add_resource("receptor")
        receptor_id_resource = receptor_resource.add_resource("{id_receptor}")

        #Agrega Certificado resource
        agrega_certificado_resource = api.root.add_resource("agrega-certificado")   

        # Consumo Timbres resource
        timbres_consumo_resource = api.root.add_resource("timbres")
        timbre_usuario_resource = timbres_consumo_resource.add_resource("{usuario}")

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

        agrega_certificado_integration = apigw.LambdaIntegration(
            agrega_certificado_lambda,
            request_templates={APPLICATION_JSON: '{ "statusCode": "200" }'}
        )

        consumo_timbres_integration = apigw.LambdaIntegration(
            timbres_consumo_lambda,
            request_templates={APPLICATION_JSON: '{ "statusCode": "200" }'}
        )

        # Certificate methods (CON CUSTOM AUTHORIZER)
        certificates_resource.add_method("POST", certificate_integration)
        certificates_resource.add_method("GET", certificate_integration, authorizer=authorizer)
        certificate_id_resource.add_method("GET", certificate_integration, authorizer=authorizer)
        certificate_id_resource.add_method("PUT", certificate_integration)
        certificate_id_resource.add_method("DELETE", certificate_integration, authorizer=authorizer)

        # Sucursal methods (CON CUSTOM AUTHORIZER)
        sucursales_resource.add_method("POST", sucursal_integration)
        sucursal_id_resource.add_method("GET", sucursal_integration)
        sucursal_id_resource.add_method("PUT", sucursal_integration)
        sucursal_id_resource.add_method("DELETE", sucursal_integration)

        # Datos Factura methods
        datos_factura.add_method("GET", datos_factura_integration)

        #Datos Tapetes methods 
        tapetes_id_resource.add_method("GET", tapetes_integration)

        #Datos Folio methods 
        folio_resource.add_method("POST", folio_integration)
        folio_id_resource.add_method("GET", folio_integration)
        folio_id_resource.add_method("PUT", folio_integration)

        #Datos Genera Factura methods 
        genera_factura.add_method("POST", genera_factura_integration)

        #Datos Receptor methods
        receptor_resource.add_method("POST", receptor_integration)
        receptor_id_resource.add_method("GET", receptor_integration)
        receptor_id_resource.add_method("PUT", receptor_integration)

        # Agrega Certificado methods
        agrega_certificado_resource.add_method("POST", agrega_certificado_integration)

        # Consumo Timbres methods
        timbre_usuario_resource.add_method("GET", consumo_timbres_integration, authorizer=authorizer)
