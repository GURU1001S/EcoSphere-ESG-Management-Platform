from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    eco_auto_emission = fields.Boolean(
        string="Auto-Emission Calculation",
        config_parameter='ecosphere.auto_emission'
    )
    eco_evidence_required = fields.Boolean(
        string="Evidence Required for CSR",
        config_parameter='ecosphere.evidence_required'
    )
    eco_badge_auto_award = fields.Boolean(
        string="Auto-Award Badges",
        config_parameter='ecosphere.badge_auto_award'
    )
    eco_policy_reminders = fields.Boolean(
        string="Automated Policy Reminders",
        config_parameter='ecosphere.policy_reminders'
    )