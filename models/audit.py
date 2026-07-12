from odoo import fields, models


class EcoAudit(models.Model):
    _name = 'eco.audit'
    _description = 'ESG Audit'

    name = fields.Char(required=True)
    department_id = fields.Many2one('eco.department')
    audit_date = fields.Date()
    findings = fields.Text()
