from aws_cdk import (
    Stack,
    aws_ecr as ecr,
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_s3 as s3,
    aws_secretsmanager as secretsmanager,
    aws_ecs_patterns as ecs_patterns,
    Reference,
)
import aws_cdk as cdk
from constructs import Construct


class IacStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        #
        # Networking
        #

        # VPC
        vpc = ec2.Vpc(
            self,
            "tubesml",
            ip_addresses=ec2.IpAddresses.cidr("10.10.0.0/16"),
            max_azs=2,
            create_internet_gateway=True,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="public", subnet_type=ec2.SubnetType.PUBLIC
                )
            ],
            enable_dns_hostnames=True,
            enable_dns_support=True,
        )

        db_credentials_secret = secretsmanager.Secret(
            self,
            "tubesml-db-credentials-secret",
            secret_name="tubesml-db-credentials",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                exclude_punctuation=True,
                include_space=False,
                password_length=20,
                secret_string_template='{"username": "tubesml"}',
                generate_string_key="password",
            ),
        )

        app_secret = secretsmanager.Secret(
            self,
            "tube-ml-app-secret",
            secret_name="tube-ml-app-secret",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                exclude_punctuation=True,
                include_space=False,
                password_length=36,
                secret_string_template="{}",
                generate_string_key="secret",
            ),
        )

        db_creds = rds.Credentials.from_secret(
            secret=db_credentials_secret,
            username="tubesml",
        )

        database = rds.DatabaseInstance(
            self,
            "tubesml-db",
            database_name="tubesml",
            instance_identifier="tubesml",
            credentials=db_creds,
            engine=rds.DatabaseInstanceEngine.maria_db(
                version=rds.MariaDbEngineVersion.VER_10_11_6
            ),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.MICRO
            ),
            allocated_storage=100,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            port=3306,
            deletion_protection=False,
            publicly_accessible=True,
            allow_major_version_upgrade=True,
        )

        database.connections.allow_default_port_internally()
        database.connections.allow_default_port_from(
            ec2.Peer.ipv4("65.163.126.128/32"),
            description="Allow access to the database from Seths home IP",
        )  # Seth's Computer

        #
        # Image Storage
        #

        # ECR Repository for API container
        ecr_repository = ecr.Repository(
            self,
            "tubesml-api",
            repository_name="tubesml-api",
        )

        # S3 Bucket for dataset storage
        dataset_bucket = s3.Bucket(
            self,
            "tubesml-dataset-bucket",
            bucket_name="tubesml-dataset",
            public_read_access=False,
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

        #
        # Compute
        #

        # ECS Cluster
        cluster = ecs.Cluster(
            self,
            "tubesml-api-cluster",
            cluster_name="tubesml-api",
            vpc=vpc,
        )

        ecs_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            "tubesml-api-service",
            cluster=cluster,
            cpu=512,
            desired_count=1,
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_ecr_repository(
                    repository=ecr_repository,
                    tag="latest",
                ),
                container_port=8000,
                secrets={
                    "DB_PASSWORD": ecs.Secret.from_secrets_manager(
                        db_credentials_secret, field="password"
                    ),
                    "SECRET_KEY": ecs.Secret.from_secrets_manager(
                        app_secret, field="secret"
                    ),
                },
                environment={
                    "DB_HOST": database.db_instance_endpoint_address,
                    "DB_PORT": database.db_instance_endpoint_port,
                    "DB_USERNAME": "tubesml",
                    "DB_NAME": "tubesml",
                    "DATASET_S3_BUCKET": dataset_bucket.bucket_name,
                },
            ),
            memory_limit_mib=1024,  # Default is 512
            public_load_balancer=True,
            assign_public_ip=True,
            service_name="tubesml-api",
            listener_port=80,
        )
