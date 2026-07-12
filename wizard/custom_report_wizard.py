from odoo import models, fields, api
from odoo.exceptions import UserError
import io
import base64
import csv
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
        ('excel', 'Raw Excel (XLSX)'),
        ('csv', 'Raw CSV')
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
        if self.export_format == 'excel':
            # Trigger the internal Excel generator
            return self._generate_excel()
        return self._generate_csv()

    def _date_domain(self, field_name):
        domain = []
        if self.date_from:
            domain.append((field_name, '>=', self.date_from))
        if self.date_to:
            domain.append((field_name, '<=', self.date_to))
        return domain

    def _get_report_rows(self):
        self.ensure_one()
        rows = []
        modules = ['environmental', 'social', 'governance', 'gamification']
        selected_modules = modules if self.module_type == 'all' else [self.module_type]

        if 'environmental' in selected_modules:
            carbon_domain = self._date_domain('date')
            goal_domain = self._date_domain('deadline')
            if self.department_id:
                carbon_domain.append(('department_id', '=', self.department_id.id))
                goal_domain.append(('department_id', '=', self.department_id.id))
            transactions = self.env['carbon.transaction'].search(carbon_domain)
            goals = self.env['esg.environmental.goal'].search(goal_domain)
            rows.append({
                'module': 'Environmental',
                'metric': 'Carbon Transactions',
                'value': len(transactions),
                'target': 'Recorded transactions',
            })
            rows.append({
                'module': 'Environmental',
                'metric': 'Total Emissions',
                'value': round(sum(transactions.mapped('total_emission')), 2),
                'target': 'kg CO2e',
            })
            rows.append({
                'module': 'Environmental',
                'metric': 'Active Goals',
                'value': len(goals.filtered(lambda g: g.status != 'achieved')),
                'target': len(goals),
            })

        if 'social' in selected_modules:
            activity_domain = self._date_domain('start_date')
            participation_domain = self._date_domain('completion_date')
            if self.department_id:
                activity_domain.append(('department_id', '=', self.department_id.id))
            if self.employee_id:
                participation_domain.append(('employee_id', '=', self.employee_id.id))
            activities = self.env['esg.csr.activity'].search(activity_domain)
            participations = self.env['esg.employee.participation'].search(participation_domain)
            rows.append({
                'module': 'Social',
                'metric': 'CSR Activities',
                'value': len(activities),
                'target': 'Activities',
            })
            rows.append({
                'module': 'Social',
                'metric': 'Approved Participations',
                'value': len(participations.filtered(lambda p: p.approval_status == 'approved')),
                'target': len(participations),
            })
            rows.append({
                'module': 'Social',
                'metric': 'Points Earned',
                'value': sum(participations.mapped('points_earned')),
                'target': 'Employee points',
            })

        if 'governance' in selected_modules:
            audit_domain = self._date_domain('date')
            if self.department_id:
                audit_domain.append(('department_id', '=', self.department_id.id))
            audits = self.env['esg.audit'].search(audit_domain)
            issues = self.env['esg.compliance.issue'].search([])
            if self.department_id:
                issues = issues.filtered(lambda issue: issue.department_id == self.department_id)
            rows.append({
                'module': 'Governance',
                'metric': 'Audits',
                'value': len(audits),
                'target': 'Audit records',
            })
            rows.append({
                'module': 'Governance',
                'metric': 'Open Compliance Issues',
                'value': len(issues.filtered(lambda i: i.status != 'resolved')),
                'target': len(issues),
            })
            rows.append({
                'module': 'Governance',
                'metric': 'Overdue Issues',
                'value': len(issues.filtered(lambda i: i.is_overdue)),
                'target': '0 overdue',
            })

        if 'gamification' in selected_modules:
            challenge_domain = self._date_domain('deadline')
            participation_domain = self._date_domain('completion_date')
            if self.department_id:
                challenge_domain.append(('department_id', '=', self.department_id.id))
            if self.challenge_id:
                participation_domain.append(('challenge_id', '=', self.challenge_id.id))
            if self.employee_id:
                participation_domain.append(('employee_id', '=', self.employee_id.id))
            challenges = self.env['esg.challenge'].search(challenge_domain)
            participations = self.env['esg.challenge.participation'].search(participation_domain)
            rows.append({
                'module': 'Gamification',
                'metric': 'Active Challenges',
                'value': len(challenges.filtered(lambda c: c.status == 'active')),
                'target': len(challenges),
            })
            rows.append({
                'module': 'Gamification',
                'metric': 'Approved Challenge Participations',
                'value': len(participations.filtered(lambda p: p.approval_status == 'approved')),
                'target': len(participations),
            })
            rows.append({
                'module': 'Gamification',
                'metric': 'XP Awarded',
                'value': sum(participations.mapped('xp_awarded')),
                'target': 'Employee XP',
            })

        return rows

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
        headers = ['Module', 'Metric', 'Value', 'Target']
        for col, header in enumerate(headers):
            sheet.write(3, col, header, bold)
        for row_index, row in enumerate(self._get_report_rows(), start=4):
            sheet.write(row_index, 0, row['module'])
            sheet.write(row_index, 1, row['metric'])
            sheet.write(row_index, 2, str(row['value']))
            sheet.write(row_index, 3, str(row['target']))
        
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

    def _generate_csv(self):
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=['module', 'metric', 'value', 'target'])
        writer.writeheader()
        writer.writerows(self._get_report_rows())
        self.write({
            'excel_file': base64.b64encode(output.getvalue().encode('utf-8')),
            'excel_filename': 'Custom_ESG_Report.csv',
            'state': 'done'
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'eco.custom.report.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
