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
            allocated_storage=100,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            port=3306,
            deletion_protection=False,
            publicly_accessible=True,
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
        # ecr_repository = ecr.Repository(
        #     self,
        #     "tubesml-api",
        #     repository_name="tubesml-api",
        # )

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
        cluster = ecs.Cluster(
            self,
            "tubesml-api-cluster",
            cluster_name="tubesml-api",
            vpc=vpc,
        )

        ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            "tubesml-api-service",
            cluster=cluster,
            cpu=512,
            desired_count=1,
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_registry("amazon/amazon-ecs-sample")
            ),
            memory_limit_mib=1024,  # Default is 512
            public_load_balancer=True,
            assign_public_ip=True,
        )
