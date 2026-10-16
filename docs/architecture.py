"""Architecture diagram as code. Regenerate with: python3 docs/architecture.py"""

from pathlib import Path

from diagrams import Cluster, Diagram, Edge
from diagrams.aws.analytics import Athena, GlueDataCatalog
from diagrams.aws.compute import Lambda
from diagrams.aws.database import Dynamodb
from diagrams.aws.devtools import Codepipeline
from diagrams.aws.integration import SNS, SQS
from diagrams.aws.management import Cloudwatch
from diagrams.aws.cost import Budgets
from diagrams.aws.security import IAMRole
from diagrams.aws.storage import S3
from diagrams.onprem.client import Users
from diagrams.onprem.vcs import Github

OUT = Path(__file__).parent / "architecture"

graph = {"pad": "0.4", "nodesep": "0.7", "ranksep": "0.9", "fontname": "Helvetica"}
node = {"fontname": "Helvetica", "fontsize": "12"}

with Diagram(
    "Serverless sales data pipeline",
    filename=str(OUT),
    outformat="png",
    show=False,
    direction="LR",
    graph_attr=graph,
    node_attr=node,
):
    branches = Users("Branches upload\nweekly sales CSV")
    analysts = Users("Analysts")

    with Cluster("AWS account (eu-west-2)"):
        raw = S3("raw bucket\nincoming/*.csv")

        with Cluster("Ingest and validate"):
            queue = SQS("files queue")
            dlq = SQS("dead-letter queue\n(after 3 failures)")
            validator = Lambda("validator\nPython 3.13, arm64")

        with Cluster("Curated data"):
            curated = S3("curated bucket\nsales/ and rejected/\npartitioned by dt=")
            audit = Dynamodb("load audit\none item per file")

        with Cluster("Query"):
            catalog = GlueDataCatalog("Glue Data Catalog\npartition projection")
            athena = Athena("Athena workgroup\n10 MB scan cap")

        with Cluster("Monitor and cost"):
            alarms = Cloudwatch("alarms\nDLQ depth, Lambda errors")
            sns = SNS("email alerts")
            budget = Budgets("budget\nalert on any spend")

    with Cluster("Delivery"):
        gh = Github("GitHub")
        ci = Codepipeline("GitHub Actions\ntests, checks, plan, apply")
        role = IAMRole("deploy role\nOIDC, no stored keys")

    branches >> raw >> Edge(label="object created") >> queue >> validator
    queue >> Edge(style="dashed", color="firebrick") >> dlq
    validator >> Edge(label="valid and\nrejected rows") >> curated
    validator >> Edge(label="status, counts") >> audit
    curated >> catalog >> athena << analysts
    dlq >> Edge(style="dashed") >> alarms
    validator >> Edge(style="dashed") >> alarms
    alarms >> sns
    budget >> sns
    gh >> ci >> role >> Edge(style="dotted", label="terraform apply") >> raw
