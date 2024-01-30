#!/usr/bin/env python3
import os

import aws_cdk as cdk

from iac.iac_stack import IacStack


app = cdk.App()

IacStack(
    app,
    "IacStack",
    env=cdk.Environment(account="533266972570", region="us-east-2"),
    # For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html
)

app.synth()
