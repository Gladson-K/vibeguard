// VibeGuard V3 parametric enclosure (OpenSCAD).
// Two-part case: rigid sensor boss + M3 stud/magnet base, USB-C and button
// openings, battery pocket and antenna keep-out. Render with F6 and export STL.

$fn = 64;

pcb_w = 50;
pcb_h = 40;
pcb_t = 1.6;
wall = 2.0;
clearance = 0.6;
case_h = 22;
lid_h = 3.0;
boss_d = 9;
boss_h = 6;
screw_d = 2.4;
stud_d = 3.4;
usb_w = 9.5;
usb_h = 3.6;
button_d = 4.2;

module rounded_box(w, h, d, r) {
    hull() {
        for (x = [-w/2 + r, w/2 - r], y = [-h/2 + r, h/2 - r])
            translate([x, y, 0]) cylinder(r = r, h = d);
    }
}

module sensor_boss() {
    translate([0, 0, wall])
        difference() {
            cylinder(d = boss_d, h = boss_h);
            translate([0, 0, boss_h - 3])
                cylinder(d = 2.2, h = 3.2); // M3 self-tapping pilot
        }
}

module pcb_standoffs() {
    inset = 3.5;
    for (x = [-pcb_w/2 + inset, pcb_w/2 - inset],
         y = [-pcb_h/2 + inset, pcb_h/2 - inset])
        translate([x, y, wall])
            difference() {
                cylinder(d = 5, h = 5);
                translate([0, 0, -0.1]) cylinder(d = 2.0, h = 5.2);
            }
}

module case() {
    difference() {
        rounded_box(pcb_w + 2*wall + 2*clearance,
                    pcb_h + 2*wall + 2*clearance,
                    case_h, 4);

        // cavity for PCB + battery
        translate([0, 0, wall])
            rounded_box(pcb_w + 2*clearance, pcb_h + 2*clearance,
                        case_h, 2);

        // USB-C opening (short end)
        translate([0, -(pcb_h/2 + wall + clearance), 8])
            rotate([90, 0, 0])
                translate([-usb_w/2, -usb_h/2, -1])
                    cube([usb_w, usb_h, wall + 2]);

        // provision button opening (long side)
        translate([pcb_w/2 + wall + clearance, 8, 8])
            rotate([0, 90, 0])
                cylinder(d = button_d, h = wall + 2);

        // lid screw holes
        inset = 3.5;
        for (x = [-pcb_w/2 + inset, pcb_w/2 - inset],
             y = [-pcb_h/2 + inset, pcb_h/2 - inset])
            translate([x, y, case_h - 6])
                cylinder(d = screw_d, h = 6.1);
    }

    sensor_boss();
    pcb_standoffs();

    // stud / magnet pocket on the mounting face
    translate([0, 0, -0.01])
        difference() {
            cylinder(d = 14, h = 1.5);
            translate([0, 0, -0.1]) cylinder(d = 12.2, h = 1.7);
        }
}

module lid() {
    difference() {
        rounded_box(pcb_w + 2*wall + 2*clearance,
                    pcb_h + 2*wall + 2*clearance,
                    lid_h, 4);
        inset = 3.5;
        for (x = [-pcb_w/2 + inset, pcb_w/2 - inset],
             y = [-pcb_h/2 + inset, pcb_h/2 - inset])
            translate([x, y, -0.1])
                rotate([0, 0, 45])
                    cylinder(d = screw_d, h = lid_h + 0.2, $fn = 6);

        // antenna keep-out vents (no metal above the module antenna)
        for (i = [0:6])
            translate([-15 + i*5, pcb_h/2 - 6, -0.1])
                cube([2, 10, lid_h + 0.2]);
    }
}

case();
translate([pcb_w + 20, 0, lid_h])
    lid();
