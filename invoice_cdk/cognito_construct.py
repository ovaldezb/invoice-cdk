
from aws_cdk import (
    Duration,
    CfnOutput,
    RemovalPolicy,
    aws_cognito as cognito,
    aws_iam as iam,
)
from constructs import Construct


class CognitoConstruct(Construct):
    """
    Construct para crear y configurar Amazon Cognito User Pool y Client
    """
    
    def __init__(self, scope: Construct, construct_id: str, postConfirmationLambda, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Crear User Pool de Cognito
        self.user_pool = cognito.UserPool(
            self, "InvoiceUserPool",
            user_pool_name="invoice-user-pool",
            self_sign_up_enabled=True,
            # Configuración de sign-in
            sign_in_aliases=cognito.SignInAliases(
                email=True,
                username=False
            ),
            # Configuración de atributos estándar
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(required=True, mutable=True),
                given_name=cognito.StandardAttribute(required=True, mutable=True),
                family_name=cognito.StandardAttribute(required=True, mutable=True)
            ),
            custom_attributes={
                "group": cognito.StringAttribute(mutable=True)
            },
            # Configuración de políticas de contraseña
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=False
            ),
            # Configuración de auto-verificación
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            # Configuración de recuperación de cuenta
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            # Eliminar protección por defecto (útil para desarrollo)
            removal_policy=RemovalPolicy.DESTROY
        )

        # Crear User Pool Client
        self.user_pool_client = cognito.UserPoolClient(
            self, "InvoiceUserPoolClient",
            user_pool=self.user_pool,
            user_pool_client_name="invoice-app-client",
            # Configuración de autenticación
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True,
                admin_user_password=True
            ),
            # Configuración de tokens
            generate_secret=False,  # Para aplicaciones públicas (SPA, mobile)
            # Duración de tokens
            access_token_validity=Duration.hours(1),
            id_token_validity=Duration.hours(1),
            refresh_token_validity=Duration.days(30)
        )

        # Crear grupos de usuarios
        self._create_user_groups()
        self.user_pool.add_trigger(
            cognito.UserPoolOperation.POST_CONFIRMATION,
            postConfirmationLambda
        )

        #permiso para lambda add users
        postConfirmationLambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["cognito-idp:AdminAddUserToGroup"],
                resources=["*"]
            )
        )
        
        
        # Crear outputs para facilitar el acceso a los recursos
        self._create_outputs()
    
    def _create_user_groups(self) -> None:
        """
        Crea los grupos de usuarios ADMIN y USER en el User Pool
        """
        # Grupo ADMIN
        self.admin_group = cognito.CfnUserPoolGroup(
            self, "AdminGroup",
            user_pool_id=self.user_pool.user_pool_id,
            group_name="ADMIN",
            description="Grupo de administradores con permisos completos",
            precedence=1  # Prioridad más alta (números más bajos = mayor prioridad)
        )
        
        # Grupo USER
        self.user_group = cognito.CfnUserPoolGroup(
            self, "UserGroup", 
            user_pool_id=self.user_pool.user_pool_id,
            group_name="USER",
            description="Grupo de usuarios estándar con permisos limitados",
            precedence=2  # Prioridad más baja
        )
    
    def _create_outputs(self) -> None:
        """
        Crea los outputs de CloudFormation para los recursos de Cognito
        """
        CfnOutput(
            self, "UserPoolId",
            value=self.user_pool.user_pool_id,
            description="ID del User Pool de Cognito",
            export_name="InvoiceUserPoolId"
        )
        
        CfnOutput(
            self, "UserPoolClientId",
            value=self.user_pool_client.user_pool_client_id,
            description="ID del User Pool Client de Cognito",
            export_name="InvoiceUserPoolClientId"
        )
        
        CfnOutput(
            self, "UserPoolArn",
            value=self.user_pool.user_pool_arn,
            description="ARN del User Pool de Cognito",
            export_name="InvoiceUserPoolArn"
        )
        
        CfnOutput(
            self, "AdminGroupName",
            value=self.admin_group.group_name,
            description="Nombre del grupo de administradores",
            export_name="InvoiceAdminGroupName"
        )
        
        CfnOutput(
            self, "UserGroupName", 
            value=self.user_group.group_name,
            description="Nombre del grupo de usuarios estándar",
            export_name="InvoiceUserGroupName"
        )
    
    @property
    def user_pool_id(self) -> str:
        """
        Retorna el ID del User Pool
        """
        return self.user_pool.user_pool_id
    
    @property
    def user_pool_client_id(self) -> str:
        """
        Retorna el ID del User Pool Client
        """
        return self.user_pool_client.user_pool_client_id
    
    @property
    def user_pool_arn(self) -> str:
        """
        Retorna el ARN del User Pool
        """
        return self.user_pool.user_pool_arn
    
    @property
    def admin_group_name(self) -> str:
        """
        Retorna el nombre del grupo ADMIN
        """
        return self.admin_group.group_name
    
    @property
    def user_group_name(self) -> str:
        """
        Retorna el nombre del grupo USER
        """
        return self.user_group.group_name
