from collections import UserString
from aws_cdk import (
    # Duration,
    Stack,
    # aws_sqs as sqs,
)
from requirements.constructs import Construct
from .lambda_functions import LambdaFunctions
from .cognito_construct import CognitoConstruct

class InvoiceCdkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here
        self.lambda_functions = LambdaFunctions(self,"LambdaFunctions")

        # Crear configuración de Cognito usando el construct separado
        self.cognito = CognitoConstruct(self, "CognitoAuth", self.lambda_functions.post_confirmation_lambda)

       

        # example resource
        # queue = sqs.Queue(
        #     self, "InvoiceCdkQueue",
        #     visibility_timeout=Duration.seconds(300),
        # )
