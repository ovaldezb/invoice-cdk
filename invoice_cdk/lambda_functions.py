from aws_cdk import aws_lambda as lambda_
from constructs import Construct
from dotenv import dotenv_values

class LambdaFunctions(Construct):
    post_confirmation_lambda: lambda_.Function
    
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        env_vars = dotenv_values(".env")
        env = {
            "VERSION":env_vars.get("VERSION"),
            "MONGO_URI": env_vars.get("MONGO_URI")
        }
        self.create_post_confirmation_lambda(env)
        
        
    def create_post_confirmation_lambda(self, env: dict):
        self.post_confirmation_lambda = lambda_.Function(
            self, "PostConfirmationLambda",
            function_name="post-confirmation-lambda",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="cognitoPostConf.handler",
            code=lambda_.Code.from_asset("invoice_cdk/lambdas"),
            environment=env
        )