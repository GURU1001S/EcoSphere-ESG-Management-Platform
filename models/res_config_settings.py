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
    eco_weight_environmental = fields.Float(
        string="Environmental Weight (%)",
        default=40.0,
        config_parameter='ecosphere.weight_environmental'
    )
    eco_weight_social = fields.Float(
        string="Social Weight (%)",
        default=30.0,
        config_parameter='ecosphere.weight_social'
    )
    eco_weight_governance = fields.Float(
        string="Governance Weight (%)",
        default=30.0,
        config_parameter='ecosphere.weight_governance'
    )
