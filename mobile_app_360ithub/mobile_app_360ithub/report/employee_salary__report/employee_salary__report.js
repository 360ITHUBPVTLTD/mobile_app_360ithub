// Copyright (c) 2025, pankaj and contributors
// For license information, please see license.txt

frappe.query_reports["Employee Salary  Report"] = {
	"filters": [
		{
			"fieldname": "fy",
			"label": __("Fiscal Year"),
			"fieldtype": "Link",
			"options": "Fiscal Year",
			reqd: true,
		},

		{
			"fieldname": "month",
			"label": __("Month"),
			"fieldtype": "Select",
			"options": "April\nMay\nJune\nJuly\nAugust\nSeptember\nOctober\nNovember\nDecember\nJanuary\nFebruary\nMarch",
			reqd: true,
		},
		{
			"fieldname": "employee",
			"label": __("Employee"),
			"fieldtype": "Link",
			"options": "Employee",
		},
	
	],
	onload: function(report) {
		
		$(document).on('click', '.dt-cell__content', function(e) {
			// 1. Ignore Header & Filters
			if ($(this).closest('.dt-header').length > 0 || $(this).closest('.dt-row-filter').length > 0) {
				return;
			}

			let $row = $(this).closest('.dt-row');
			
			// Check if the row we just clicked is ALREADY expanded
			let wasAlreadyExpanded = $row.hasClass('is-expanded');

			// 2. RESET absolutely all rows back to default state
			$('.dt-row').removeClass('is-expanded').css({
				'height': '', 
				'z-index': '',
				'box-shadow': '',
				'background-color': '',
				'border-top': '',
				'border-bottom': ''
			});
			$('.dt-cell').css({
				'height': '',
				'background-color': '',
				'overflow': ''
			});
			$('.dt-cell__content').removeClass('highlighted-cell')
				.css({
					'white-space': '',
					'overflow': '',
					'font-weight': '',
					'padding-top': '',
					'padding-bottom': '',
					'height': '',
					'display': '',
					'align-items': ''
				});

			// 3. THE TOGGLE: If it was already expanded, stop here! (It is now collapsed)
			if (wasAlreadyExpanded) {
				return;
			}

			// 4. APPLY STYLES TO NEWLY CLICKED ROW (If it wasn't expanded)
			$row.addClass('is-expanded'); // Mark this row as expanded
			
			// Style the ENTIRE ROW as a single unified block
			$row.css({
				'height': 'auto',       
				'z-index': '999',       
				'box-shadow': '0px 6px 16px rgba(0,0,0,0.12)', 
				'background-color': '#e1effe', 
				'border-top': '2px solid #93c5fd', 
				'border-bottom': '2px solid #93c5fd'

			});

			// Let the cells expand, making them transparent so the row color shows
			$row.find('.dt-cell').css({
				'height': 'auto',
				'background-color': 'transparent', 
				'overflow': 'visible'
			});

			// Format the text content inside the cells nicely
			$row.find('.dt-cell__content').each(function() {
				$(this).addClass('highlighted-cell')
					.css({
						'white-space': 'normal',   
						'word-wrap': 'break-word',
						'font-weight': '600',      
						'padding-top': '10px',     
						'padding-bottom': '10px',
						'height': '100%',          
						'display': 'flex',         
						'align-items': 'center'    
					});
			});
		});
	}
};
