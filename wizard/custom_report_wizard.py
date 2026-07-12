from odoo import fields, models


class EcoReportWizard(models.TransientModel):
    _name = 'eco.report.wizard'
    _description = 'Custom ESG Report Wizard'

    name = fields.Char(default='ESG Report')
    start_date = fields.Date()
    end_date = fields.Date()

    def action_generate_report(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'ESG Report',
            'res_model': 'eco.report.wizard',
            'view_mode': 'form',
            'target': 'new',
        }
