variable "region" {
  type    = string
  default = "eu-west-2"
}

variable "name" {
  description = "Prefix for every resource name"
  type        = string
  default     = "ssp"
}

variable "alert_email" {
  description = "Receives pipeline failure alarms and budget alerts"
  type        = string
}

variable "branches" {
  description = "Branch codes a sales file may contain"
  type        = list(string)
  default     = ["LON01", "LON02", "MAN01", "DUB01", "AMS01", "BER01"]
}

variable "monthly_budget_usd" {
  description = "Budget alert threshold. Alerts at 1% (any spend at all) and at 100%."
  type        = number
  default     = 1
}
