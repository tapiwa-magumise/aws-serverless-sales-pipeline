# Glue Data Catalog tables over the curated bucket, queried with Athena.
# Partition projection means no Glue crawler (crawlers are billed per run)
# and no MSCK REPAIR: Athena works out the dt= partitions from the table settings.

resource "aws_glue_catalog_database" "sales" {
  name = "${var.name}_sales"
}

locals {
  projection = {
    "projection.enabled"          = "true"
    "projection.dt.type"          = "date"
    "projection.dt.format"        = "yyyy-MM-dd"
    "projection.dt.range"         = "2026-01-01,NOW"
    "projection.dt.interval"      = "1"
    "projection.dt.interval.unit" = "DAYS"
  }
}

resource "aws_glue_catalog_table" "sales" {
  name          = "sales"
  database_name = aws_glue_catalog_database.sales.name
  table_type    = "EXTERNAL_TABLE"

  parameters = merge(local.projection, {
    "classification"            = "json"
    "storage.location.template" = "s3://${aws_s3_bucket.this["curated"].id}/sales/dt=$${dt}/"
  })

  partition_keys {
    name = "dt"
    type = "string"
  }

  storage_descriptor {
    location      = "s3://${aws_s3_bucket.this["curated"].id}/sales/"
    input_format  = "org.apache.hadoop.mapred.TextInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat"

    ser_de_info {
      serialization_library = "org.openx.data.jsonserde.JsonSerDe"
    }

    columns {
      name = "date"
      type = "date"
    }
    columns {
      name = "branch_code"
      type = "string"
    }
    columns {
      name = "sku"
      type = "string"
    }
    columns {
      name = "units"
      type = "int"
    }
    columns {
      name = "revenue"
      type = "decimal(12,2)"
    }
    columns {
      name = "cost"
      type = "decimal(12,2)"
    }
  }
}

resource "aws_glue_catalog_table" "rejected" {
  name          = "rejected"
  database_name = aws_glue_catalog_database.sales.name
  table_type    = "EXTERNAL_TABLE"

  parameters = merge(local.projection, {
    "classification"            = "json"
    "storage.location.template" = "s3://${aws_s3_bucket.this["curated"].id}/rejected/dt=$${dt}/"
  })

  partition_keys {
    name = "dt"
    type = "string"
  }

  storage_descriptor {
    location      = "s3://${aws_s3_bucket.this["curated"].id}/rejected/"
    input_format  = "org.apache.hadoop.mapred.TextInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat"

    ser_de_info {
      serialization_library = "org.openx.data.jsonserde.JsonSerDe"
    }

    # Rejected rows keep their raw text, so every column is a string.
    dynamic "columns" {
      for_each = ["date", "branch_code", "sku", "units", "revenue", "cost"]
      content {
        name = columns.value
        type = "string"
      }
    }
    columns {
      name = "line"
      type = "int"
    }
    columns {
      name = "reasons"
      type = "array<string>"
    }
  }
}

resource "aws_athena_workgroup" "sales" {
  name          = "${var.name}-sales"
  force_destroy = true

  configuration {
    enforce_workgroup_configuration = true
    # Hard cap per query (10 MB is Athena's minimum). Stops a runaway scan.
    bytes_scanned_cutoff_per_query = 10485760

    result_configuration {
      output_location = "s3://${aws_s3_bucket.this["results"].id}/"
      encryption_configuration { encryption_option = "SSE_S3" }
    }
  }
}

resource "aws_athena_named_query" "daily_margin" {
  name      = "daily-margin-by-branch"
  workgroup = aws_athena_workgroup.sales.name
  database  = aws_glue_catalog_database.sales.name
  query     = <<-SQL
    SELECT date, branch_code,
           SUM(units)          AS units,
           SUM(revenue)        AS revenue,
           SUM(revenue - cost) AS margin
    FROM sales
    GROUP BY date, branch_code
    ORDER BY date, branch_code;
  SQL
}

resource "aws_athena_named_query" "rejection_reasons" {
  name      = "rejection-reasons"
  workgroup = aws_athena_workgroup.sales.name
  database  = aws_glue_catalog_database.sales.name
  query     = <<-SQL
    SELECT reason, COUNT(*) AS rows
    FROM rejected CROSS JOIN UNNEST(reasons) AS t(reason)
    GROUP BY reason
    ORDER BY rows DESC;
  SQL
}
