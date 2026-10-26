#!/bin/bash
H=/h/hzm_work/ice1025_build
$H/build_then_test.sh t15 obj/obj_team3 oh1,oh3,oh2 --gpu || exit 1
