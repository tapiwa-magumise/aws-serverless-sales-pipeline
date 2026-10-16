"""Generate the two .drawio files for the serverless pipeline repo."""
import sys
from html import escape

OUTDIR = sys.argv[1]

C = {"storage": "#7AA116", "integration": "#E7157B", "compute": "#ED7100", "database": "#C925D1",
     "analytics": "#8C4FFF", "management": "#E7157B", "security": "#DD344C", "cost": "#7AA116"}
INK = "#232F3E"
EDGE = "#545B64"
RED = "#D13212"


class Doc:
    def __init__(self, name, w, h):
        self.name, self.w, self.h = name, w, h
        self.cells = []
        self.n = 2
        self.org = {"1": (0, 0)}  # absolute origin of each container; all coordinates passed in are absolute

    def _id(self):
        self.n += 1
        return f"c{self.n}"

    def add(self, value, style, x, y, w, h, parent="1", vertex=True):
        i = self._id()
        value = value.replace("\n", "<br>")
        self.org[i] = (x, y)
        px, py = self.org[parent]
        x, y = x - px, y - py
        self.cells.append(
            f'<mxCell id="{i}" value="{escape(value)}" style="{style}" vertex="1" parent="{parent}">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')
        return i

    def group(self, label, kind, x, y, w, h, parent="1", fs=12):
        styles = {
            "cloud": f"grIcon=mxgraph.aws4.group_aws_cloud_alt;strokeColor={INK};fontColor={INK};dashed=0;",
            "region": "grIcon=mxgraph.aws4.group_region;strokeColor=#00A4A6;fontColor=#147EBA;dashed=1;",
            "account": "grIcon=mxgraph.aws4.group_account;strokeColor=#CD2264;fontColor=#CD2264;dashed=0;",
        }
        st = ("points=[];outlineConnect=0;gradientColor=none;html=1;whiteSpace=wrap;fontSize=%d;fontStyle=1;"
              "container=1;pointerEvents=0;collapsible=0;recursiveResize=0;shape=mxgraph.aws4.group;"
              "fillColor=none;verticalAlign=top;align=left;spacingLeft=30;" % fs) + styles[kind]
        return self.add(label, st, x, y, w, h, parent)

    def box(self, label, x, y, w, h, parent="1", color="#879196", fs=12):
        st = (f"fillColor=none;strokeColor={color};dashed=1;verticalAlign=top;fontStyle=1;fontColor={color};"
              f"whiteSpace=wrap;html=1;align=left;spacingLeft=10;spacingTop=4;fontSize={fs};rounded=1;arcSize=3;container=1;collapsible=0;")
        return self.add(label, st, x, y, w, h, parent)

    @staticmethod
    def lab(pos):
        return {"below": "verticalLabelPosition=bottom;verticalAlign=top;align=center;",
                "above": "verticalLabelPosition=top;verticalAlign=bottom;align=center;",
                "right": "labelPosition=right;verticalLabelPosition=middle;align=left;verticalAlign=middle;spacingLeft=4;",
                "left": "labelPosition=left;verticalLabelPosition=middle;align=right;verticalAlign=middle;spacingRight=4;"}[pos]

    def res(self, label, icon, cat, x, y, parent="1", s=64, fs=12, pos="below"):
        st = (f"sketch=0;outlineConnect=0;fontColor={INK};gradientColor=none;fillColor={C[cat]};strokeColor=#ffffff;"
              f"dashed=0;html=1;fontSize={fs};" + self.lab(pos) +
              f"aspect=fixed;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.{icon};")
        return self.add(label, st, x, y, s, s, parent)

    def shape(self, label, shp, color, x, y, w=52, h=52, parent="1", fs=12, pos="below"):
        st = (f"sketch=0;outlineConnect=0;fontColor={INK};gradientColor=none;fillColor={color};strokeColor=none;"
              f"dashed=0;html=1;fontSize={fs};" + self.lab(pos) +
              f"aspect=fixed;pointerEvents=1;shape=mxgraph.aws4.{shp};")
        return self.add(label, st, x, y, w, h, parent)

    def text(self, label, x, y, w, h, fs=12, bold=False, color=INK, align="left", parent="1"):
        st = (f"text;html=1;strokeColor=none;fillColor=none;align={align};verticalAlign=top;whiteSpace=wrap;"
              f"fontSize={fs};fontColor={color};fontStyle={1 if bold else 0};")
        return self.add(label, st, x, y, w, h, parent)

    def badge(self, n, x, y, parent="1", d=24, fs=12):
        st = (f"ellipse;whiteSpace=wrap;html=1;aspect=fixed;fillColor={INK};strokeColor=none;fontColor=#FFFFFF;"
              f"fontStyle=1;fontSize={fs};")
        return self.add(str(n), st, x, y, d, d, parent)

    def chip(self, label, x, y, w, h, fs=12):
        st = (f"rounded=1;arcSize=50;whiteSpace=wrap;html=1;fillColor=#EAF0F8;strokeColor=#C4D2E6;fontColor=#1F4E9C;"
              f"fontStyle=1;fontSize={fs};")
        return self.add(label, st, x, y, w, h)

    def gh(self, label, x, y, w=150, h=56, parent="1", fs=12):
        st = (f"rounded=1;whiteSpace=wrap;html=1;fillColor={INK};strokeColor=none;fontColor=#FFFFFF;fontStyle=1;"
              f"fontSize={fs};")
        return self.add(label, st, x, y, w, h, parent)

    def edge(self, src, dst, label="", color=EDGE, dashed=False, w=2, ex=None, ey=None, nx=None, ny=None, fs=11, via=None):
        i = self._id()
        st = (f"edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;endFill=1;strokeColor={color};"
              f"strokeWidth={w};fontSize={fs};fontColor={color};labelBackgroundColor=#FFFFFF;"
              + ("dashed=1;dashPattern=6 4;" if dashed else ""))
        if ex is not None:
            st += f"exitX={ex};exitY={ey};exitDx=0;exitDy=0;"
        if nx is not None:
            st += f"entryX={nx};entryY={ny};entryDx=0;entryDy=0;"
        self.cells.append(
            f'<mxCell id="{i}" value="{escape(label.replace(chr(10), "<br>"))}" style="{st}" edge="1" parent="1" source="{src}" target="{dst}">'
            f'<mxGeometry relative="1" as="geometry">'
            + ('<Array as="points">' + "".join(f'<mxPoint x="{px}" y="{py}"/>' for px, py in via) + '</Array>' if via else "")
            + '</mxGeometry></mxCell>')
        return i

    def xml(self):
        return (f'<mxfile host="drawio"><diagram name="{escape(self.name)}">'
                f'<mxGraphModel dx="0" dy="0" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" '
                f'fold="1" page="1" pageScale="1" pageWidth="{self.w}" pageHeight="{self.h}" background="#FFFFFF" math="0" shadow="0">'
                '<root><mxCell id="0"/><mxCell id="1" parent="0"/>'
                + "".join(self.cells) + "</root></mxGraphModel></diagram></mxfile>")



# =====================================================================
# 1. Detailed architecture (README). All coordinates absolute.
# =====================================================================
d = Doc("Serverless sales data pipeline", 2000, 1080)
d.add("", "rounded=0;fillColor=#FFFFFF;strokeColor=none;", 0, 0, 2000, 1080)
d.text("Serverless sales data pipeline", 30, 20, 900, 34, fs=24, bold=True)
d.text("Reference architecture · every resource defined in Terraform", 30, 56, 900, 22, fs=14, color="#545B64")

cloud = d.group("AWS Cloud", "cloud", 150, 100, 1330, 950)
region = d.group("Region: eu-west-2 (London)", "region", 180, 150, 1270, 640, parent=cloud)

ingest = d.box("Ingest and validate", 210, 200, 600, 380, parent=region)
raw = d.res("Raw bucket (S3)\nincoming/*.csv", "s3", "storage", 250, 330, parent=ingest)
queue = d.res("Files queue (SQS)", "sqs", "integration", 460, 330, parent=ingest, pos="above")
lam = d.res("Validator\n(Lambda, Python 3.13)", "lambda", "compute", 680, 330, parent=ingest)
dlq = d.res("Dead-letter queue (SQS)\nafter 3 failures", "sqs", "integration", 460, 480, parent=ingest)

lake = d.box("Data lake and audit", 840, 200, 280, 380, parent=region)
curated = d.res("Curated bucket (S3)\nsales/ · rejected/ · dt=", "s3", "storage", 948, 330, parent=lake)
audit = d.res("Load audit table\n(DynamoDB)", "dynamodb", "database", 948, 470, parent=lake)

query = d.box("Query", 1150, 200, 270, 380, parent=region)
catalog = d.shape("Glue Data Catalog\npartition projection", "glue_data_catalog", C["analytics"], 1182, 334, 56, 56, parent=query)
athena = d.res("Athena workgroup\n10 MB scan cap", "athena", "analytics", 1320, 330, parent=query)

mon = d.box("Monitoring, alerting and cost", 210, 610, 1210, 160, parent=region)
budget = d.res("Budget (AWS Budgets)\nemails on any spend", "budgets", "cost", 300, 650, parent=mon, pos="right")
alarms = d.res("CloudWatch alarms\nDLQ depth · Lambda errors", "cloudwatch_2", "management", 760, 645, parent=mon, pos="below")
sns = d.res("Alerts topic\n(SNS, email)", "sns", "integration", 1180, 645, parent=mon, pos="below")

iam = d.box("IAM (global)", 180, 830, 940, 190, parent=cloud, color="#DD344C")
lrole = d.shape("Validator execution role\nleast privilege", "role", C["security"], 230, 905, 70, 40, parent=iam, pos="right")
oidc = d.res("GitHub OIDC\nidentity provider", "identity_and_access_management", "security", 560, 885, parent=iam, pos="below")
drole = d.shape("Deploy role\nmain branch + pull requests", "role", C["security"], 860, 897, 70, 40, parent=iam, pos="below")

staff = d.shape("Branch staff", "users", INK, 40, 332, 60, 60)
analysts = d.shape("Analysts", "users", INK, 1530, 332, 60, 60)
ops = d.shape("Operations", "users", INK, 1530, 652, 60, 60, pos="right")
gha = d.gh("GitHub Actions\ntest · scan · plan · apply", 1500, 893, 200, 64)
repo = d.gh("GitHub repository\nTerraform + Python", 1500, 985, 200, 50)

d.edge(staff, raw, "upload CSV")
d.edge(raw, queue, "object created")
d.edge(queue, lam)
d.edge(queue, dlq, color=RED, dashed=True)
d.edge(lam, curated, "valid + rejected rows")
d.edge(lam, audit, "status, counts", ex=1, ey=0.8, nx=0, ny=0.5)
d.edge(curated, catalog)
d.edge(catalog, athena)
d.edge(analysts, athena, "SQL")
d.edge(dlq, alarms, color=RED, dashed=True, ex=1, ey=0.5, nx=0.5, ny=0)
d.edge(alarms, sns, color=RED, dashed=True)
d.edge(sns, ops, "email", color=RED, dashed=True)
d.edge(budget, ops, "email", color="#7AA116", dashed=True, ex=0.5, ey=1, nx=0.5, ny=1, via=[(332, 758), (1560, 758)])
d.edge(repo, gha, ex=0.5, ey=0, nx=0.5, ny=1)
d.edge(gha, drole, "assume role\nwith OIDC token", color="#DD344C", dashed=True, w=1.5)
d.edge(drole, oidc, "trusts", color="#DD344C", dashed=True, w=1.5)
d.edge(drole, region, "terraform apply", color="#DD344C", dashed=True, w=1.5, ex=0.5, ey=0, nx=0.55, ny=1)

for n, x, y in [(1, 135, 312), (2, 330, 312), (3, 600, 312), (4, 780, 312), (5, 860, 452),
                (6, 1468, 312), (7, 600, 470), (8, 270, 640), (9, 1470, 875)]:
    d.badge(n, x, y)

lx = 1730
d.text("How it works", lx, 100, 250, 24, fs=15, bold=True)
steps = [
    "Branch staff upload a sales CSV to the raw bucket.",
    "S3 sends an event to the SQS queue, which buffers bursts and retries failures.",
    "Lambda validates every row. At most 2 copies run at once.",
    "Valid rows, and rejected rows with reasons, go to the curated bucket by date.",
    "Each file gets one audit record. A conditional write blocks duplicates.",
    "Analysts query with Athena. Glue Data Catalog describes the files.",
    "After 3 failures a file moves to the dead-letter queue and an alarm emails operations.",
    "A budget alert emails on any spend.",
    "GitHub Actions deploys with a short-lived OIDC token. No stored keys.",
]
y = 136
for i, s_ in enumerate(steps, 1):
    d.badge(i, lx, y, d=20, fs=11)
    d.text(s_, lx + 28, y - 2, 230, 64, fs=12)
    y += 62
d.text("Legend", lx, y + 8, 250, 20, fs=13, bold=True)
d.text("Grey line: data flow\nRed dashed: failure and alerting\nPink dashed: identity and deployment\nGreen dashed: cost alert",
       lx, y + 30, 250, 80, fs=12, color="#545B64")

open(f"{OUTDIR}/architecture.drawio", "w").write(d.xml())

# =====================================================================
# 2. LinkedIn: 540x675 page, exported at 2x = 1080x1350
# =====================================================================
L = Doc("LinkedIn", 540, 675)
L.add("", "rounded=0;fillColor=#FFFFFF;strokeColor=none;", 0, 0, 540, 675)
L.text("Serverless sales data pipeline", 22, 20, 500, 30, fs=23, bold=True)
L.text("On AWS in London, built with Terraform, runs at $0", 22, 52, 500, 22, fs=14, color="#545B64")

staff = L.shape("Branch staff upload a sales CSV", "users", INK, 120, 86, 40, 40, fs=12, pos="right")
lcloud = L.group("AWS Cloud", "cloud", 16, 140, 508, 410, fs=11)
lreg = L.group("eu-west-2", "region", 26, 172, 488, 368, parent=lcloud, fs=11)

S = 44
A, B, Cc = 118, 262, 392
R = [222, 316, 410, 486]
raw = L.res("Raw files (S3)", "s3", "storage", A, R[0], parent=lreg, s=S, fs=11, pos="below")
q = L.res("Queue (SQS)", "sqs", "integration", B, R[0], parent=lreg, s=S, fs=11, pos="above")
dlq = L.res("Dead-letter\nqueue (SQS)", "sqs", "integration", Cc, R[0], parent=lreg, s=S, fs=11, pos="right")
fn = L.res("Validate\nevery row\n(Lambda)", "lambda", "compute", B, R[1], parent=lreg, s=S, fs=11, pos="right")
alarm = L.res("Alarm\n(CloudWatch)", "cloudwatch_2", "management", Cc, R[1], parent=lreg, s=S, fs=11, pos="right")
cur = L.res("Clean and\nrejected rows\n(S3)", "s3", "storage", A, R[2], parent=lreg, s=S, fs=11, pos="right")
aud = L.res("Audit trail\n(DynamoDB)", "dynamodb", "database", B, R[2], parent=lreg, s=S, fs=11, pos="right")
sns = L.res("Email alert\n(SNS)", "sns", "integration", Cc, R[2], parent=lreg, s=S, fs=11, pos="right")
ath = L.res("SQL reports\n(Athena)", "athena", "analytics", A, R[3], parent=lreg, s=36, fs=11, pos="right")

L.edge(staff, raw, nx=0.5, ny=0)
L.edge(raw, q)
L.edge(q, dlq, color=RED, dashed=True)
L.edge(q, fn)
L.edge(fn, cur, ex=0, ey=0.5, nx=0.5, ny=0)
L.edge(fn, aud)
L.edge(cur, ath, nx=0.5, ny=0)
L.edge(dlq, alarm, color=RED, dashed=True)
L.edge(alarm, sns, color=RED, dashed=True)

for n, x, y in [(1, 186, 222), (2, 290, 290), (3, 96, 380), (4, 96, 470), (5, 350, 222)]:
    L.badge(n, x, y, d=18, fs=10)

items = ["File lands in S3 and is queued", "Lambda checks every row",
         "Clean data, rejects and audit saved", "Analysts query with SQL", "Failures retried 3x, then emailed"]
for i, s_ in enumerate(items):
    col, row = i % 2, i // 2
    x = 22 + col * 256
    yy = 566 + row * 22
    L.badge(i + 1, x, yy, d=16, fs=9)
    L.text(s_, x + 22, yy - 1, 230, 20, fs=11)

L.text("Deployed by GitHub Actions with OIDC: no stored AWS keys.", 22, 636, 500, 18, fs=11)
L.text("github.com/gumagatsby/aws-serverless-sales-pipeline", 22, 654, 500, 18, fs=11, color="#545B64")
open(f"{OUTDIR}/linkedin-architecture.drawio", "w").write(L.xml())
print("ok")
