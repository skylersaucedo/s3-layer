from aws_cdk import (
    Stack,
    aws_ecr as ecr,
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_s3 as s3,
    aws_secretsmanager as secretsmanager,
)
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
            "tubesml-vpc",
            ip_addresses=ec2.IpAddresses.cidr("172.30.0.0/16"),
            max_azs=3,
            nat_gateways=1,
            create_internet_gateway=True,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="tubesml-subnet-1",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="tubesml-subnet-2",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                    map_public_ip_on_launch=True,
                ),
                ec2.SubnetConfiguration(
                    name="tubesml-subnet-3",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                    map_public_ip_on_launch=True,
                ),
            ],
        )

        #
        # Storage
        #

        # S3 bucket for dataset storage
        dataset_s3_bucket = s3.Bucket(
            self, "tubesml-datasets", bucket_name="tubesml-datasets"
        )

        # S3 bucket for model storage
        models_s3_bucket = s3.Bucket(
            self, "tubesml-models", bucket_name="tubesml-models"
        )

        #
        # Secrets
        #

        # Secrets Manager Secret for DB password
        # db_password_secret = secretsmanager.Secret(
        #     self,
        #     "tubesml-db-password",
        #     secret_name="tubesml-db-password",
        #     description="Password for the tubesml database",
        #     generate_secret_string=secretsmanager.SecretStringGenerator(
        #         exclude_punctuation=True
        #     ),
        # )

        #
        # Databases
        #

        database = rds.DatabaseInstance(
            self,
            "tubesml-db",
            database_name="tubesml",
            instance_identifier="tubesml",
            credentials=rds.Credentials.from_generated_secret(
                username="tubesml", secret_name="tubesml-db-password"
            ),
            engine=rds.DatabaseInstanceEngine.MARIADB,
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.MICRO
            ),
            vpc=vpc,
            port=3306,
            deletion_protection=False,
            publicly_accessible=True,
        )

        #
        # Image Storage
        #

        # ECR Repository for API container
        ecr_repository = ecr.Repository(
            self,
            "tubesml-api",
            repository_name="tubesml-api",
        )

        # We have a chicken-and-egg problem, because we just created the ECR repo but have not
        # yet pushed an image to it, so we're going to use a test image to get the ECS service
        # running and then we'll update the image in the deployment pipeline.
        # container_image = ecs.ContainerImage.from_ecr_repository(
        #     repository=ecr_repository,
        #     tag="latest",
        # )

        #
        # Compute
        #

        # # ECS Cluster
        # cluster = ecs.Cluster(
        #     self,
        #     "tubesml-api-cluster",
        #     cluster_name="tubesml-api",
        #     vpc=vpc,
        # )

        # # ECS Task Definition
        # task_definition = ecs.FargateTaskDefinition(
        #     self,
        #     "tubesml-api-task",
        #     cpu=256,
        #     memory_limit_mib=512,
        # )

        # # ECS Task Container
        # container = task_definition.add_container(
        #     "tubesml-api-container",
        #     image=container_image,
        #     container_name="tubesml-api",
        #     logging=ecs.LogDrivers.aws_logs(
        #         aws_logs_stream_prefix="tubesml-api",
        #         aws_logs_group=ecs.LogGroup(
        #             self, "tubesml-api-logs", log_group_name="tubesml-api"
        #         ),
        #         log_retention=ecs.RetentionDays.ONE_WEEK,
        #     ),
        #     environment={
        #         "DEBUG": "False",
        #         "DB_HOST": "quimby-lite.claa0id5irim.us-east-2.rds.amazonaws.com",
        #         "DB_NAME": "quimby",
        #         "DB_USER": "quimby",
        #     },
        #     secrets={"DB_PASSWORD": db_password_secret},
        #     port_mappings=[ecs.PortMapping(container_port=8000)],
        # )

        # # ECS Service
        # service = ecs.FargateService(
        #     self,
        #     "tubesml-api-service",
        #     cluster=cluster,
        #     service_name="tubesml-api",
        #     desired_count=1,
        #     task_definition=task_definition,
        # )
