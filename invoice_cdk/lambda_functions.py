from aws_cdk import Duration, aws_lambda as lambda_
from constructs import Construct
from dotenv import dotenv_values

class LambdaFunctions(Construct):
    post_confirmation_lambda: lambda_.Function
    certificate_lambda: lambda_.Function
    sucursal_lambda: lambda_.Function

    pymongo_layer: lambda_.LayerVersion
    
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        env_vars = dotenv_values(".env")
        env = {
            "VERSION":env_vars.get("VERSION"),
            "MONGODB_URI": f"mongodb+srv://{env_vars.get("MONGO_USER")}:{env_vars.get("MONGO_PW")}@{env_vars.get("MONGO_HOST")}/{env_vars.get("MONGO_DB")}?retryWrites=true&w=majority",
            "DB_NAME": env_vars.get("MONGO_DB"),
            
        }
        pymongo_layer = lambda_.LayerVersion(
            self, "pymongo-layer",
            code=lambda_.Code.from_asset("lambda_layers"),  # Directory with requirements
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_12],
            description="Capa con pymongo"
        )
        self.create_post_confirmation_lambda(env)
        self.create_certificate_lambda(env, pymongo_layer)
        self.create_sucursal_lambda(env, pymongo_layer)

    def create_post_confirmation_lambda(self, env: dict,):
        self.post_confirmation_lambda = lambda_.Function(
            self, "PostConfirmationLambda",
            function_name="post-confirmation-lambda-invoice",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="cognitoPostConf.handler",
            code=lambda_.Code.from_asset("invoice_cdk/lambdas"),
            environment=env
        )

    def create_certificate_lambda(self, env: dict, pymongo_layer: lambda_.LayerVersion):
        self.certificate_lambda = lambda_.Function(
            self, "CertificateLambda",
            function_name="certificate-lambda-invoice",
            description="Lambda function to handle certificate operations",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="certificates_handler.handler",
            code=lambda_.Code.from_asset("invoice_cdk/lambdas"),
            layers=[pymongo_layer],  # Add the layer to the Lambda function
            environment=env,
            timeout=Duration.seconds(10)  # Optional: Set a timeout for the Lambda function
        )

    def create_sucursal_lambda(self, env: dict, pymongo_layer: lambda_.LayerVersion):
        self.sucursal_lambda = lambda_.Function(
            self, "SucursalLambda",
            function_name="sucursal-lambda-invoice",
            description="Lambda function to handle branch operations",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="sucursal_handler.handler",
            code=lambda_.Code.from_asset("invoice_cdk/lambdas"),
            layers=[pymongo_layer],  # Add the layer to the Lambda function
            environment=env,
            timeout=Duration.seconds(50)  # Optional: Set a timeout for the Lambda function
        )

    """def create_usuario_lambda(self, env: dict, pymongo_layer: lambda_.LayerVersion):
        self.usuario_lambda = lambda_.Function(
            self, "UsuarioLambda",
            function_name="usuario-lambda-invoice",
            description="Lambda function to handle user operations",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="usuarios_handler.handler",
            code=lambda_.Code.from_asset("invoice_cdk/lambdas"),
            layers=[pymongo_layer],  # Add the layer to the Lambda function
            environment=env,
            timeout=Duration.seconds(10)  # Optional: Set a timeout for the Lambda function
        )"""
