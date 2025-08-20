from aws_cdk import Duration, aws_lambda as lambda_
from constructs import Construct
from dotenv import dotenv_values

class LambdaFunctions(Construct):
    post_confirmation_lambda: lambda_.Function
    certificate_lambda: lambda_.Function
    sucursal_lambda: lambda_.Function
    custom_authorizer_lambda: lambda_.Function
    datos_factura_lambda: lambda_.Function

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
        
        # Layer para custom authorizer
        authorizer_layer = lambda_.LayerVersion(
            self, "authorizer-layer",
            code=lambda_.Code.from_asset("authorizer_layer"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_12],
            description="Capa con PyJWT y requests para authorizer"
        )
        
        self.create_post_confirmation_lambda(env)
        self.create_certificate_lambda(env, pymongo_layer)
        self.create_sucursal_lambda(env, pymongo_layer)
        self.create_custom_authorizer_lambda(env, authorizer_layer)
        self.create_datos_factura_lambda(env, pymongo_layer)

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

    def create_custom_authorizer_lambda(self, env: dict, authorizer_layer: lambda_.LayerVersion):
        self.custom_authorizer_lambda = lambda_.Function(
            self, "CustomAuthorizerLambda",
            function_name="custom-authorizer-lambda-invoice",
            description="Lambda function for custom authorization",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="simple_authorizer.handler",
            code=lambda_.Code.from_asset("invoice_cdk/lambdas"),
            layers=[authorizer_layer],
            environment=env,
            timeout=Duration.seconds(30)
        )

    def create_datos_factura_lambda(self, env: dict, pymongo_layer: lambda_.LayerVersion):
        self.datos_factura_lambda = lambda_.Function(
            self, "DatosFacturaLambda",
            function_name="datos-factura-lambda-invoice",
            description="Lambda function to handle datos para factura",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="datos_factura_handler.handler",
            code=lambda_.Code.from_asset("invoice_cdk/lambdas"),
            layers=[pymongo_layer],  # Add the layer to the Lambda function
            environment=env,
            timeout=Duration.seconds(10)  # Optional: Set a timeout for the Lambda function
        )