from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_cognito as cognito,  # Import cognito
    aws_iam as iam,
    aws_apigateway as apigw,  # Import apigateway (si no está ya importado)
)
from constructs import Construct

from .lambda_functions import LambdaFunctions
from .cognito_construct import CognitoConstruct
from .certificado_apigateway import CertificateApiGateway

class InvoiceCdkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        # Crear rol para que API Gateway escriba en CloudWatch Logs

        # The code that defines your stack goes here
        self.lambda_functions = LambdaFunctions(self,"LambdaFunctions")

        # Crear configuración de Cognito usando el construct separado
        self.cognito_invoice = CognitoConstruct(self, "CognitoAuth", self.lambda_functions.post_confirmation_lambda)
        

        lambdas = {
            "certificate_lambda": self.lambda_functions.certificate_lambda,
            "sucursal_lambda": self.lambda_functions.sucursal_lambda,
            "datos_factura_lambda": self.lambda_functions.datos_factura_lambda,
            "tapetes_lambda": self.lambda_functions.tapetes_lambda,
            "folio_lambda": self.lambda_functions.folio_lambda,
            "genera_factura_lambda": self.lambda_functions.genera_factura_lambda,
            "receptor_lambda": self.lambda_functions.receptor_lambda,
            "maneja_certificado_lambda": self.lambda_functions.maneja_certificado_lambda,
            "timbres_consumo_lambda": self.lambda_functions.timbres_consumo_lambda,
            "parsea_pdf_regimen_lambda": self.lambda_functions.parsea_pdf_regimen_lambda,
            "environment_handler_lambda": self.lambda_functions.environment_handler_lambda
        }
        # Create API Gateway for the certificate lambda
        CertificateApiGateway(self, "CertificateApiGateway", lambdas, self.cognito_invoice.user_pool_cognito)

        #AngularHost(self, "AngularHostStack")
