from aws_cdk import (
    aws_lambda as _lambda,
    aws_apigateway as apigw,
    aws_cognito as cognito
)
from constructs import Construct

class CertificateApiGateway(Construct):
    def __init__(self, scope: Construct, id: str, certificate_lambda: _lambda.Function, usuario_lambda: _lambda.Function, user_pool_id: str):
        super().__init__(scope, id)
        self.create_ApiGw_certificate_lambda(certificate_lambda, user_pool_id)
        self.create_ApiGw_usuario_lambda(usuario_lambda, user_pool_id)

    def create_ApiGw_certificate_lambda(self, certificate_lambda: _lambda.Function, user_pool_id: str):
        api = apigw.RestApi(
            self,
            "CertificateAPI",
            rest_api_name="Certificate API",
            description="This service manages certificates.",
            default_cors_preflight_options={
                "allow_origins": ['*'],
                "allow_methods": ['OPTIONS','GET','POST','PUT','DELETE'],
                "allow_headers": ["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key", "X-Amz-Security-Token"],
                "allow_credentials": True
            }
        )

        # Create a Cognito User Pool authorizer
        authorizer = apigw.CognitoUserPoolsAuthorizer(
            self,
            "CertificateAPIAuthorizer",
            cognito_user_pools=[cognito.UserPool.from_user_pool_id(self, "CertificatePool", user_pool_id)],
            authorizer_name="CertificateAuthorizer"
        )

        certificates_resource = api.root.add_resource("certificados")

        # POST /certificates
        certificates_integration = apigw.LambdaIntegration(
            certificate_lambda,
            request_templates={"application/json": '{ "statusCode": "200" }'}
        )
        certificates_resource.add_method("POST", certificates_integration)

        # GET /certificates
        certificates_resource.add_method("GET", certificates_integration)

        # /{id} resource
        certificate_id_resource = certificates_resource.add_resource("{id}")

        # GET /certificates/{id}  (optional, if you want to get a specific certificate)
        certificate_id_resource.add_method("GET", certificates_integration, authorizer=authorizer)

        # PUT /certificates/{id}
        certificate_id_resource.add_method("PUT", certificates_integration, authorizer=authorizer)

        # DELETE /certificates/{id}
        certificate_id_resource.add_method("DELETE", certificates_integration, authorizer=authorizer)
        
    def create_ApiGw_usuario_lambda(self, usuario_lambda: _lambda.Function, user_pool_id: str):
        api = apigw.RestApi(
            self,
            "UsuarioAPI",
            rest_api_name="Usuario API",
            description="This service manages users.",
            default_cors_preflight_options={
                "allow_origins": ['*'],
                "allow_methods": ['OPTIONS','GET','POST','PUT','DELETE'],
                "allow_headers": ["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key", "X-Amz-Security-Token"],
                "allow_credentials": True
            }
        )

        # Create a Cognito User Pool authorizer
        authorizer = apigw.CognitoUserPoolsAuthorizer(
            self,
            "UsuarioAPIAuthorizer",
            cognito_user_pools=[cognito.UserPool.from_user_pool_id(self, "UserPool", user_pool_id)],
            authorizer_name="UsuarioAuthorizer"
        )

        usuarios_resource = api.root.add_resource("usuarios")

        # POST /usuarios
        usuarios_integration = apigw.LambdaIntegration(
            usuario_lambda,
            request_templates={"application/json": '{ "statusCode": "200" }'}
        )
        usuarios_resource.add_method("POST", usuarios_integration)

        # GET /usuarios
        usuarios_resource.add_method("GET", usuarios_integration)

        # /{id} resource
        usuario_id_resource = usuarios_resource.add_resource("{id}")

        # GET /usuarios/{id}  (optional, if you want to get a specific user)
        usuario_id_resource.add_method("GET", usuarios_integration, authorizer=authorizer)

        # PUT /usuarios/{id}
        usuario_id_resource.add_method("PUT", usuarios_integration, authorizer=authorizer)

        # DELETE /usuarios/{id}
        usuario_id_resource.add_method("DELETE", usuarios_integration, authorizer=authorizer)