from aws_cdk import Duration, aws_lambda as lambda_
from constructs import Construct
from dotenv import dotenv_values

INVOICE_LAMBDAS_PATH = "invoice_cdk/lambdas"
class LambdaFunctions(Construct):
    post_confirmation_lambda: lambda_.Function
    certificate_lambda: lambda_.Function
    sucursal_lambda: lambda_.Function
    custom_authorizer_lambda: lambda_.Function
    datos_factura_lambda: lambda_.Function
    tapetes_lambda: lambda_.Function
    folio_lambda: lambda_.Function
    genera_factura_lambda: lambda_.Function
    receptor_lambda: lambda_.Function
    agrega_certificado_lambda: lambda_.Function
    timbres_consumo_lambda: lambda_.Function

    pymongo_layer: lambda_.LayerVersion
    
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        env_vars = dotenv_values(".env")
        env = {
            "VERSION":env_vars.get("VERSION"),
            "MONGODB_URI": f"mongodb+srv://{env_vars.get("MONGO_USER")}:{env_vars.get("MONGO_PW")}@{env_vars.get("MONGO_HOST")}/{env_vars.get("MONGO_DB")}?retryWrites=true&w=majority",
            "DB_NAME": env_vars.get("MONGO_DB"),
            
        }
        env_tapetes = {
            "MONGODB_URI": f"mongodb+srv://{env_vars.get("MONGO_USER")}:{env_vars.get("MONGO_PW")}@{env_vars.get("MONGO_HOST")}/{env_vars.get("MONGO_DB")}?retryWrites=true&w=majority",
            "DB_NAME": env_vars.get("MONGO_DB"),
            "TAPETES_API_URL": env_vars.get("TAPETES_API_URL"),
            "TAPETES_USER_NAME": env_vars.get("TAPETES_USER_NAME"),
            "TAPETES_PASSWORD": env_vars.get("TAPETES_PASSWORD")
        }

        env_fact ={
            "SW_USER_NAME": env_vars.get("SW_USER_NAME"),
            "SW_USER_PASSWORD": env_vars.get("SW_USER_PASSWORD"),
            "SW_URL": env_vars.get("SW_URL"),
            "TAPETES_API_URL": env_vars.get("TAPETES_API_URL"),
            "TAPETES_USER_NAME": env_vars.get("TAPETES_USER_NAME"),
            "TAPETES_PASSWORD": env_vars.get("TAPETES_PASSWORD"),
            "MONGODB_URI": f"mongodb+srv://{env_vars.get("MONGO_USER")}:{env_vars.get("MONGO_PW")}@{env_vars.get("MONGO_HOST")}/{env_vars.get("MONGO_DB")}?retryWrites=true&w=majority",
            "DB_NAME": env_vars.get("MONGO_DB"),
            "SMTP_HOST": env_vars.get("SMTP_HOST"),
            "SMTP_PORT": env_vars.get("SMTP_PORT"),
            "SMTP_USER": env_vars.get("SMTP_USER"),
            "SMTP_PASSWORD": env_vars.get("SMTP_PASSWORD")
        }

        env_cert = {
            "SW_USER_NAME": env_vars.get("SW_USER_NAME"),
            "SW_USER_PASSWORD": env_vars.get("SW_USER_PASSWORD"),
            "SW_URL": env_vars.get("SW_URL")
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
        self.create_tapetes_lambda(env_tapetes, pymongo_layer)
        self.create_folio_lambda(env, pymongo_layer)
        self.create_genera_factura_lambda(env_fact, pymongo_layer)
        self.create_receptor_lambda(env, pymongo_layer)
        self.create_agrega_certificado_lambda(env_cert, pymongo_layer)
        self.create_timbres_consumo_lambda(env, pymongo_layer)

    def create_post_confirmation_lambda(self, env: dict,):
        self.post_confirmation_lambda = lambda_.Function(
            self, "PostConfirmationLambda",
            function_name="post-confirmation-lambda-invoice",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="cognitoPostConf.handler",
            code=lambda_.Code.from_asset(INVOICE_LAMBDAS_PATH),
            environment=env
        )

    def create_certificate_lambda(self, env: dict, pymongo_layer: lambda_.LayerVersion):
        self.certificate_lambda = lambda_.Function(
            self, "CertificateLambda",
            function_name="certificate-lambda-invoice",
            description="Lambda function to handle certificate operations",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="certificates_handler.handler",
            code=lambda_.Code.from_asset(INVOICE_LAMBDAS_PATH),
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
            code=lambda_.Code.from_asset(INVOICE_LAMBDAS_PATH),
            layers=[pymongo_layer],  # Add the layer to the Lambda function
            environment=env,
            timeout=Duration.seconds(10)  # Optional: Set a timeout for the Lambda function
        )

    def create_custom_authorizer_lambda(self, env: dict, authorizer_layer: lambda_.LayerVersion):
        self.custom_authorizer_lambda = lambda_.Function(
            self, "CustomAuthorizerLambda",
            function_name="custom-authorizer-lambda-invoice",
            description="Lambda function for custom authorization",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="simple_authorizer.handler",
            code=lambda_.Code.from_asset(INVOICE_LAMBDAS_PATH),
            layers=[authorizer_layer],
            environment=env,
            timeout=Duration.seconds(10)
        )

    def create_datos_factura_lambda(self, env: dict, pymongo_layer: lambda_.LayerVersion):
        self.datos_factura_lambda = lambda_.Function(
            self, "DatosFacturaLambda",
            function_name="datos-factura-lambda-invoice",
            description="Lambda function to handle datos para factura",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="datos_factura_handler.handler",
            code=lambda_.Code.from_asset(INVOICE_LAMBDAS_PATH),
            layers=[pymongo_layer],  # Add the layer to the Lambda function
            environment=env,
            timeout=Duration.seconds(10)  # Optional: Set a timeout for the Lambda function
        )

    def create_tapetes_lambda(self, env_tapetes: dict, pymongo_layer: lambda_.LayerVersion):
        self.tapetes_lambda = lambda_.Function(
            self, "TapetesLambda",
            function_name="tapetes-lambda-invoice",
            description="Lambda function to handle tapetes operations",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="tapetes_handler.handler",
            code=lambda_.Code.from_asset(INVOICE_LAMBDAS_PATH),
            layers=[pymongo_layer],  # Add the layer to the Lambda function
            environment=env_tapetes,
            timeout=Duration.seconds(10)  # Optional: Set a timeout for the Lambda function
        )

    def create_folio_lambda(self, env: dict, pymongo_layer: lambda_.LayerVersion):
        self.folio_lambda = lambda_.Function(
            self, "FolioLambda",
            function_name="folio-lambda-invoice",
            description="Lambda function to handle folio operations",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="folio_handler.handler",
            code=lambda_.Code.from_asset(INVOICE_LAMBDAS_PATH),
            layers=[pymongo_layer],  # Add the layer to the Lambda function
            environment=env,
            timeout=Duration.seconds(10)  # Optional: Set a timeout for the Lambda function
        )

    def create_genera_factura_lambda(self, env: dict, pymongo_layer: lambda_.LayerVersion):
        self.genera_factura_lambda = lambda_.Function(
            self, "GeneraFacturaLambda",
            function_name="genera-factura-lambda-invoice",
            description="Lambda function to handle factura generation",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="genera_factura_handler.handler",
            code=lambda_.Code.from_asset(INVOICE_LAMBDAS_PATH),
            layers=[pymongo_layer],
            environment=env,
            timeout=Duration.seconds(10)
        )

    def create_receptor_lambda(self, env: dict, pymongo_layer: lambda_.LayerVersion):
        self.receptor_lambda = lambda_.Function(
            self, "ReceptorLambda",
            function_name="receptor-lambda-invoice",
            description="Lambda function to handle receptor operations",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="receptor_handler.handler",
            code=lambda_.Code.from_asset(INVOICE_LAMBDAS_PATH),
            layers=[pymongo_layer],
            environment=env,
            timeout=Duration.seconds(10)
        )

    def create_agrega_certificado_lambda(self, env: dict, pymongo_layer: lambda_.LayerVersion):
        self.agrega_certificado_lambda = lambda_.Function(
            self, "AgregaCertificadoLambda",
            function_name="agrega-certificado-lambda-invoice",
            description="Lambda function to handle adding certificates",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="agrega_certificado_handler.handler",
            code=lambda_.Code.from_asset(INVOICE_LAMBDAS_PATH),
            layers=[pymongo_layer],
            environment=env,
            timeout=Duration.seconds(10)
        )

    def create_timbres_consumo_lambda(self, env: dict, pymongo_layer: lambda_.LayerVersion):
        self.timbres_consumo_lambda = lambda_.Function(
            self, "TimbresConsumoLambda",
            function_name="timbres-consumo-lambda-invoice",
            description="Lambda function to handle timbres consumo operations",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="consumo_timbres_handler.lambda_handler",
            code=lambda_.Code.from_asset(INVOICE_LAMBDAS_PATH),
            layers=[pymongo_layer],
            environment=env,
            timeout=Duration.seconds(10)
        )
