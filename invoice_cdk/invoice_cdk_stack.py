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
        
        alias = {
            "certificate_alias": self.lambda_functions.certificate_alias,
            "sucursal_alias": self.lambda_functions.sucursal_alias,
            "datos_factura_alias": self.lambda_functions.datos_factura_alias,
            "tapetes_alias": self.lambda_functions.tapetes_alias,
            "folio_alias": self.lambda_functions.folio_alias,
            "genera_factura_alias": self.lambda_functions.genera_factura_alias,
            "receptor_alias": self.lambda_functions.receptor_alias,
            "maneja_certificado_alias": self.lambda_functions.maneja_certificado_alias,
            "timbres_consumo_alias": self.lambda_functions.timbres_consumo_alias,
            "parsea_pdf_regimen_alias": self.lambda_functions.parsea_pdf_regimen_alias,
            "environment_handler_alias": self.lambda_functions.environment_handler_alias,
            "bitacora_alias": self.lambda_functions.bitacora_alias
        }
        # Create API Gateway for the certificate lambda
        CertificateApiGateway(self, "CertificateApiGateway", alias, self.cognito_invoice.user_pool_cognito)

        #AngularHost(self, "AngularHostStack")
