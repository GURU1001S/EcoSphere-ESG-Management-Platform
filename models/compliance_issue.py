from odoo import fields, models


class EcoComplianceIssue(models.Model):
    _name = 'eco.compliance.issue'
    _description = 'Compliance Issue'

    name = fields.Char(required=True)
    department_id = fields.Many2one('eco.department')
    date_reported = fields.Date()
    severity = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ], default='medium')
