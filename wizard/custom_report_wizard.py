from odoo import models, fields, api
from odoo.exceptions import UserError
import io
import base64
try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None

class EcoCustomReportWizard(models.TransientModel):
    _name = 'eco.custom.report.wizard'
    _description = 'Custom ESG Report Builder'

    # 1. Master Filters
    module_type = fields.Selection([
        ('all', 'All Modules'),
        ('environmental', 'Environmental'),
        ('social', 'Social'),
        ('governance', 'Governance'),
        ('gamification', 'Gamification')
    ], string='Target Module', default='all', required=True)
    
    export_format = fields.Selection([
        ('pdf', 'PDF Summary'),
        ('excel', 'Raw Excel (XLSX)')
    ], string='Output Format', default='pdf', required=True)

    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    department_id = fields.Many2one('esg.department', string='Department')

    # 2. Dynamic/Conditional Filters
    employee_id = fields.Many2one('hr.employee', string='Employee')
    challenge_id = fields.Many2one('esg.challenge', string='Challenge')
    category_id = fields.Many2one('esg.category', string='ESG Category')

    # 3. Export Handlers
    state = fields.Selection([('draft', 'Draft'), ('done', 'Done')], default='draft')
    excel_file = fields.Binary('Excel File', readonly=True)
    excel_filename = fields.Char('Excel Filename', readonly=True)

    def action_generate_report(self):
        # Route the signal based on the selected output format
        if self.export_format == 'pdf':
            # Trigger the QWeb PDF engine
            return self.env.ref('ecosphere.action_report_esg_custom').report_action(self)
        else:
            # Trigger the internal Excel generator
            return self._generate_excel()

    def _generate_excel(self):
        if xlsxwriter is None:
            raise UserError("The xlsxwriter Python package is required to export Excel reports.")

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('ESG Export')
        
        # Simple Header Formatting
        bold = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3'})
        sheet.write(0, 0, 'ESG Report - Data Export', bold)
        sheet.write(1, 0, f'Module: {dict(self._fields["module_type"].selection).get(self.module_type)}')
        
        # Note: Your teammates will pipe their database query results here.
        # For now, we generate the file structure to prove the framework functions.
        
        workbook.close()
        output.seek(0)
        
        # Flip the UI state to show the download button
        self.write({
            'excel_file': base64.b64encode(output.read()),
            'excel_filename': 'Custom_ESG_Report.xlsx',
            'state': 'done'
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'eco.custom.report.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
