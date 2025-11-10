from aws_cdk import Duration, aws_lambda as lambda_, RemovalPolicy
from constructs import Construct
from dotenv import dotenv_values

INVOICE_LAMBDAS_PATH = "invoice_cdk/lambdas"
class LambdaFunctions(Construct):
    post_confirmation_lambda: lambda_.Function
    certificate_lambda: lambda_.Function
    sucursal_lambda: lambda_.Function
    #custom_authorizer_lambda: lambda_.Function
    datos_factura_lambda: lambda_.Function
    tapetes_lambda: lambda_.Function
    folio_lambda: lambda_.Function
    genera_factura_lambda: lambda_.Function
    receptor_lambda: lambda_.Function
    maneja_certificado_lambda: lambda_.Function
    timbres_consumo_lambda: lambda_.Function
    parsea_pdf_regimen_lambda: lambda_.Function
    environment_handler_lambda: lambda_.Function

    pymongo_layer: lambda_.LayerVersion
    
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        env_vars = dotenv_values(".env")
        env = {
            "VERSION":env_vars.get("VERSION"),
            "MONGODB_URI": f"mongodb+srv://{env_vars.get("MONGO_USER")}:{env_vars.get("MONGO_PW")}@{env_vars.get("MONGO_HOST")}/{env_vars.get("MONGO_DB")}?retryWrites=true&w=majority",
            "DB_NAME": env_vars.get("MONGO_DB"),
            "CORS": env_vars.get("CORS"),
            "ENV": env_vars.get("ENV")
        }
        env_cors = {
            "CORS": env_vars.get("CORS"),
            "ENV": env_vars.get("ENV")
        }
        env_tapetes = {
            "MONGODB_URI": f"mongodb+srv://{env_vars.get("MONGO_USER")}:{env_vars.get("MONGO_PW")}@{env_vars.get("MONGO_HOST")}/{env_vars.get("MONGO_DB")}?retryWrites=true&w=majority",
            "DB_NAME": env_vars.get("MONGO_DB"),
            "TAPETES_API_URL": env_vars.get("TAPETES_API_URL"),
            "TAPETES_USER_NAME": env_vars.get("TAPETES_USER_NAME"),
            "TAPETES_PASSWORD": env_vars.get("TAPETES_PASSWORD"),
            "CORS": env_vars.get("CORS"),
            "ENV": env_vars.get("ENV")
        }

        env_fact ={
            "SW_USER_NAME": env_vars.get("SW_USER_NAME"),
            "SW_USER_PASSWORD": env_vars.get("SW_USER_PASSWORD"),
            "SW_URL": env_vars.get("SW_URL"),
            "TAPETES_API_URL": env_vars.get("TAPETES_API_URL"),
            "TAPETES_USER_NAME": env_vars.get("TAPETES_USER_NAME"),
            "TAPETES_PASSWORD": env_vars.get("TAPETES_PASSWORD"),
            "MONGODB_URI": f"mongodb+srv://{env_vars.get("MONGO_USER")}:{env_vars.get("MONGO_PW")}@{env_vars.get("MONGO_HOST")}/{env_vars.get("MONGO_DB")}?retryWrites=true&w=majority",
            "DB_NAME":       env_vars.get("MONGO_DB"),
            "SMTP_HOST":     env_vars.get("SMTP_HOST"),
            "SMTP_PORT":     env_vars.get("SMTP_PORT"),
            "SMTP_USER":     env_vars.get("SMTP_USER"),
            "SMTP_PASSWORD": env_vars.get("SMTP_PASSWORD"),
            "SMTP_FROM":     env_vars.get("SMTP_FROM"),
            "SMTP_REPLY_TO": env_vars.get("SMTP_REPLY_TO"),
            "SMTP_BCC":      env_vars.get("SMTP_BCC"),
            "CORS":          env_vars.get("CORS"),
            "ENV":           env_vars.get("ENV")
        }

        env_cert = {
            "SW_USER_NAME": env_vars.get("SW_USER_NAME"),
            "SW_USER_PASSWORD": env_vars.get("SW_USER_PASSWORD"),
            "SW_URL": env_vars.get("SW_URL"),
            "CORS": env_vars.get("CORS"),
            "MONGODB_URI": f"mongodb+srv://{env_vars.get("MONGO_USER")}:{env_vars.get("MONGO_PW")}@{env_vars.get("MONGO_HOST")}/{env_vars.get("MONGO_DB")}?retryWrites=true&w=majority",
            "DB_NAME": env_vars.get("MONGO_DB"),
            "ENV": env_vars.get("ENV")
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
        self.create_datos_factura_lambda(env, pymongo_layer)
        self.create_tapetes_lambda(env_tapetes, pymongo_layer)
        self.create_folio_lambda(env, pymongo_layer)
        self.create_genera_factura_lambda(env_fact, pymongo_layer)
        self.create_receptor_lambda(env, pymongo_layer)
        self.create_maneja_certificado_lambda(env_cert, pymongo_layer)
        self.create_timbres_consumo_lambda(env, pymongo_layer)
        self.create_parsea_pdf_regimen_lambda(env_cors,pymongo_layer)
        self.create_environment_handler_lambda(env_cors,pymongo_layer)

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
            timeout=Duration.seconds(10),  # Optional: Set a timeout for the Lambda function
            current_version_options=lambda_.VersionOptions(
                removal_policy=RemovalPolicy.RETAIN
            )
        )
        version = self.certificate_lambda.current_version
        self.certificate_alias = lambda_.Alias(
            self, "CertificateLambdaAlias",
            alias_name="Prod",
            version=version
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
            timeout=Duration.seconds(10),  # Optional: Set a timeout for the Lambda function
            current_version_options=lambda_.VersionOptions(
                removal_policy=RemovalPolicy.RETAIN
            )
        )
        self.sucursal_alias = lambda_.Alias(
            self, "SucursalLambdaAlias",
            alias_name="Prod",
            version=self.sucursal_lambda.current_version
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
            timeout=Duration.seconds(10),  # Optional: Set a timeout for the Lambda function
            current_version_options=lambda_.VersionOptions(
                removal_policy=RemovalPolicy.RETAIN
            )
        )
        self.datos_factura_alias = lambda_.Alias(
            self, "DatosFacturaLambdaAlias",
            alias_name="Prod",
            version=self.datos_factura_lambda.current_version
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
            timeout=Duration.seconds(10),  # Optional: Set a timeout for the Lambda function
            current_version_options=lambda_.VersionOptions(
                removal_policy=RemovalPolicy.RETAIN
            )
        )
        self.tapetes_alias = lambda_.Alias(
            self, "TapetesLambdaAlias",
            alias_name="Prod",
            version=self.tapetes_lambda.current_version
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
            timeout=Duration.seconds(10),  # Optional: Set a timeout for the Lambda function
            current_version_options=lambda_.VersionOptions(
                removal_policy=RemovalPolicy.RETAIN
            )
        )
        self.folio_alias = lambda_.Alias(
            self, "FolioLambdaAlias",
            alias_name="Prod",
            version=self.folio_lambda.current_version
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
            timeout=Duration.seconds(10),
            current_version_options=lambda_.VersionOptions(
                removal_policy=RemovalPolicy.RETAIN
            )
        )
        self.genera_factura_alias = lambda_.Alias(
            self, "GeneraFacturaLambdaAlias",
            alias_name="Prod",
            version=self.genera_factura_lambda.current_version
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
            timeout=Duration.seconds(10),
            current_version_options=lambda_.VersionOptions(
                removal_policy=RemovalPolicy.RETAIN
            )
        )
        self.receptor_alias = lambda_.Alias(
            self, "ReceptorLambdaAlias",
            alias_name="Prod",
            version=self.receptor_lambda.current_version
        )

    def create_maneja_certificado_lambda(self, env: dict, pymongo_layer: lambda_.LayerVersion):
        self.maneja_certificado_lambda = lambda_.Function(
            self, "ManejaCertificadoLambda",
            function_name="maneja-certificado-lambda-invoice",
            description="Lambda function to handle adding certificates",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="maneja_certificado_handler.handler",
            code=lambda_.Code.from_asset(INVOICE_LAMBDAS_PATH),
            layers=[pymongo_layer],
            environment=env,
            timeout=Duration.seconds(10),
            current_version_options=lambda_.VersionOptions(
                removal_policy=RemovalPolicy.RETAIN
            )
        )
        self.maneja_certificado_alias = lambda_.Alias(
            self, "ManejaCertificadoLambdaAlias",
            alias_name="Prod",
            version=self.maneja_certificado_lambda.current_version
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
            timeout=Duration.seconds(10),
            current_version_options=lambda_.VersionOptions(
                removal_policy=RemovalPolicy.RETAIN
            )
        )
        self.timbres_consumo_alias = lambda_.Alias(
            self, "TimbresConsumoLambdaAlias",
            alias_name="Prod",
            version=self.timbres_consumo_lambda.current_version
        )

    def create_parsea_pdf_regimen_lambda(self, env: dict, pymongo_layer: lambda_.LayerVersion):
        self.parsea_pdf_regimen_lambda = lambda_.Function(
            self, "ParseaPDFRegimenLambda",
            function_name="parsea-pdf-regimen-lambda-invoice",
            description="Lambda function to parse PDF and extract regimen fiscal",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="parse_regimen_handler.handler",
            code=lambda_.Code.from_asset(INVOICE_LAMBDAS_PATH),
            layers=[pymongo_layer],
            environment=env,
            timeout=Duration.seconds(30),
            current_version_options=lambda_.VersionOptions(
                removal_policy=RemovalPolicy.RETAIN
            )
        )
        self.parsea_pdf_regimen_alias = lambda_.Alias(
            self, "ParseaPDFRegimenLambdaAlias",
            alias_name="Prod",
            version=self.parsea_pdf_regimen_lambda.current_version
        )

    def create_environment_handler_lambda(self, env: dict, pymongo_layer: lambda_.LayerVersion):
        self.environment_handler_lambda = lambda_.Function(
            self, "EnvironmentHandlerLambda",
            function_name="environment-handler-lambda-invoice",
            description="Lambda function to handle environment variable requests",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="environment_handler.handler",
            code=lambda_.Code.from_asset(INVOICE_LAMBDAS_PATH),
            layers=[pymongo_layer],
            environment=env,
            timeout=Duration.seconds(10),
            current_version_options=lambda_.VersionOptions(
                removal_policy=RemovalPolicy.RETAIN
            )
        )
        self.environment_handler_alias = lambda_.Alias(
            self, "EnvironmentHandlerLambdaAlias",
            alias_name="Prod",
            version=self.environment_handler_lambda.current_version
        )