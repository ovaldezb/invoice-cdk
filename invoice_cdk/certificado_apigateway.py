from aws_cdk import (
    Duration,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
    aws_cognito as cognito
)
from constructs import Construct

class CertificateApiGateway(Construct):
    def __init__(self, scope: Construct, id: str, certificate_lambda: _lambda.Function, sucursal_lambda: _lambda.Function, datos_factura_lambda: _lambda.Function, invoice_pool: cognito.UserPool, custom_authorizer_lambda: _lambda.Function = None):
        super().__init__(scope, id)

        # Create a single RestApi instance
        api = apigw.RestApi(
            self,
            "InvoiceAPI",
            rest_api_name="Invoice API",
            description="This service manages certificates and branches.",
            default_cors_preflight_options={
                "allow_origins": ['*'],
                "allow_methods": ['OPTIONS','GET','POST','PUT','DELETE'],
                "allow_headers": ["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key", "X-Amz-Security-Token"],
                "allow_credentials": True
            }
        )

        # Create authorizer (preferir custom authorizer si está disponible)
        if custom_authorizer_lambda:
            authorizer = apigw.TokenAuthorizer(
                self,
                "CustomTokenAuthorizer",
                handler=custom_authorizer_lambda,
                authorizer_name="CustomInvoiceAuthorizer"
            )
        else:
            # Fallback a Cognito User Pool authorizer
            authorizer = apigw.CognitoUserPoolsAuthorizer(
                self,
                "InvoiceAPIAuthorizer",
                cognito_user_pools=[invoice_pool],
                authorizer_name="InvoiceAuthorizer",
                identity_source="method.request.header.Authorization"
            )

        # Certificates resources
        certificates_resource = api.root.add_resource("certificados")
        certificate_id_resource = certificates_resource.add_resource("{id}")

        # Sucursales resources
        sucursales_resource = api.root.add_resource("sucursales")
        sucursal_id_resource = sucursales_resource.add_resource("{id}")

        # Datos Factura resources
        datos_factura = api.root.add_resource("datosfactura")

        # Integrations
        certificate_integration = apigw.LambdaIntegration(
            certificate_lambda,
            request_templates={"application/json": '{ "statusCode": "200" }'}
        )

        sucursal_integration = apigw.LambdaIntegration(
            sucursal_lambda,
            request_templates={"application/json": '{ "statusCode": "200" }'}
        )

        datos_factura_integration = apigw.LambdaIntegration(
            datos_factura_lambda,
            request_templates={"application/json": '{ "statusCode": "200" }'}
        )

        # Certificate methods (CON CUSTOM AUTHORIZER)
        certificates_resource.add_method("POST", certificate_integration)
        certificates_resource.add_method("GET", certificate_integration, authorizer=authorizer)
        certificate_id_resource.add_method("GET", certificate_integration, authorizer=authorizer)
        certificate_id_resource.add_method("PUT", certificate_integration)
        certificate_id_resource.add_method("DELETE", certificate_integration)

        # Sucursal methods (CON CUSTOM AUTHORIZER)
        sucursales_resource.add_method("POST", sucursal_integration)
        sucursales_resource.add_method("GET", sucursal_integration)
        sucursal_id_resource.add_method("GET", sucursal_integration)
        sucursal_id_resource.add_method("PUT", sucursal_integration)
        sucursal_id_resource.add_method("DELETE", sucursal_integration)

        # Datos Factura methods (CON CUSTOM AUTHORIZER)
        datos_factura.add_method("GET", datos_factura_integration)