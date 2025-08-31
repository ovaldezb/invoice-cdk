from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_cognito as cognito  # Import cognito
)
from constructs import Construct
from .angular_host_stack import AngularHost
from .lambda_functions import LambdaFunctions
from .cognito_construct import CognitoConstruct
from .certificado_apigateway import CertificateApiGateway

class InvoiceCdkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here
        self.lambda_functions = LambdaFunctions(self,"LambdaFunctions")

        # Crear configuración de Cognito usando el construct separado
        self.cognito_invoice = CognitoConstruct(self, "CognitoAuth", self.lambda_functions.post_confirmation_lambda)

        # Create API Gateway for the certificate lambda
        CertificateApiGateway(self, "CertificateApiGateway", 
                            self.lambda_functions.certificate_lambda, 
                            self.lambda_functions.sucursal_lambda, 
                            self.lambda_functions.datos_factura_lambda,
                            self.lambda_functions.tapetes_lambda,
                            self.lambda_functions.folio_lambda,
                            self.lambda_functions.genera_factura_lambda,
                            self.lambda_functions.receptor_lambda,
                            self.cognito_invoice.user_pool,
                            self.lambda_functions.custom_authorizer_lambda)

        AngularHost(self, "AngularHostStack")
