from aws_cdk import aws_lambda as lambda_
from constructs import Construct
from dotenv import dotenv_values

class LambdaFunctions(Construct):
    post_confirmation_lambda: lambda_.Function
    certificate_lambda: lambda_.Function
    
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        env_vars = dotenv_values(".env")
        env = {
            "VERSION":env_vars.get("VERSION"),
            "MONGODB_URI": f"mongodb+srv://{env_vars.get("MONGO_USER")}:{env_vars.get("MONGO_PW")}@{env_vars.get("MONGO_HOST")}/{env_vars.get("MONGO_DB")}?retryWrites=true&w=majority",
            "DB_NAME": env_vars.get("MONGO_DB"),
            
        }
        self.create_post_confirmation_lambda(env)
        self.create_certificate_lambda(env)
        
        
    def create_post_confirmation_lambda(self, env: dict):
        self.post_confirmation_lambda = lambda_.Function(
            self, "PostConfirmationLambda",
            function_name="post-confirmation-lambda",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="cognitoPostConf.handler",
            code=lambda_.Code.from_asset("invoice_cdk/lambdas"),
            environment=env
        )

    def create_certificate_lambda(self, env: dict):
        # Define a Lambda Layer
        pymongo_layer = lambda_.LayerVersion(
            self, "pymongo-layer",
            code=lambda_.Code.from_asset("lambda_layers"),  # Directory with requirements
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_12],
            description="Capa con pymongo"
        )

        self.certificate_lambda = lambda_.Function(
            self, "CertificateLambda",
            function_name="certificate-lambda",
            description="Lambda function to handle certificate operations",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="certificates_handler.handler",
            code=lambda_.Code.from_asset("invoice_cdk/lambdas"),
            layers=[pymongo_layer],  # Add the layer to the Lambda function
            environment=env
        )
