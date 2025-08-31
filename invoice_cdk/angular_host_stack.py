from aws_cdk import (
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    RemovalPolicy
)
from constructs import Construct

class AngularHost(Construct):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        site_bucket = s3.Bucket(self, "AngularSiteBucket",
            bucket_name="sistema-facturacion-chiposoft",  # Cambia esto por un nombre único
            website_index_document="index.html",
            website_error_document="index.html",
            public_read_access=True,
            block_public_access=s3.BlockPublicAccess(block_public_acls=False, ignore_public_acls=False, block_public_policy=False, restrict_public_buckets=False),  # <-- Agrega esta línea
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        s3deploy.BucketDeployment(self, "DeployAngularWebsite",
            sources=[s3deploy.Source.asset("/Users/macbookpro/git/invoice-front-end/dist/invoice-front-end")],
            destination_bucket=site_bucket,
            prune=True
        )
