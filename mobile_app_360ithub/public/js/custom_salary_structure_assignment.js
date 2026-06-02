frappe.ui.form.on('Salary Structure Assignment', {
    refresh: function(frm) {
        
    },
    employee: function(frm) {
        // if(frm.doc.__islocal){
        if(true){
            if(! frm.doc.base){
                frappe.call({
                    method: 'clarity_360ithub.custom_employee.get_base_salary',
                    args: {
                        employee: frm.doc.employee,
                       
                    },
                    callback: function(resBaseSal) {
                        if (resBaseSal.message) {
                            frm.set_value('base', resBaseSal.message);
                            frm.refresh_field('base');
                        } 
                    },
                });
            }
            
        }
    },
    validate: function(frm) {
        if(!frm.doc.base || frm.doc.base <= 0){
            frappe.throw(__("Please enter base salary"));
        }
    }
});