# Material-Interface-Generation
Examples of generating graded material transitions using VoxelFuse

## strength_test_coupon

`strength_test_coupon_mm3dp.py` - Demonstrates generating tensile test coupons with graded material transitions. Transition properties are set using the files in the `config_files` folder. Multiple config IDs can be specified to generate multiple coupons at once.

`combine_models.py` - Combine a series of tensile test coupon .vf files into a single file

`lattice_element.py` - Test the min and max dilation values for a single lattice element

`viewer.py` - Load and display a .vf file

__Pre-configured Patterns__

&nbsp;&nbsp; A. No transition <br>
&nbsp;&nbsp; B. Blur <br>
&nbsp;&nbsp; C. 3D Dither <br>
&nbsp;&nbsp; D. 2D Dither <br>
&nbsp;&nbsp; E. Gyroid <br>
&nbsp;&nbsp; F. P-surface <br>
&nbsp;&nbsp; G. D-surface <br>
&nbsp;&nbsp; H. Plus lattice <br>
&nbsp;&nbsp; I. Cross lattice <br>
&nbsp;&nbsp; J. Small fibers <br>
&nbsp;&nbsp; K. Large fibers

__Example Outputs__

- V2 - Original coupon set, 11 material steps
- V3 - Extended coupon set (adds 2D dither and small fibers), 6 material steps
- V4.1 - Coupon set V3 normalized to give a consistent elastic modulus

![tensile test coupon example image](../master/strength_test_coupon/stl_files_v2_combined/assembled_components.png?raw=true)

![tensile test coupon example print](../master/strength_test_coupon/all-samples-1.jpg?raw=true)

## dithering
`dither.py` - Functions for applying 3D dithering to a model

`thin.py` - Function for finding the 3D centerline of a model

`centerline-test.py` - Test the `thin` function

`viewer.py` - Load and display a .vf file

![dither example image](../master/dithering/dither-example.png?raw=true)

## gyroid
`gyroid.py` - Test the functions for generating triply periodic surfaces

![gyroid example image](../master/gyroid/gyroid-element-1.png?raw=true)

## lattice_transition
`lattice_transition.py` - Demonstrates generating a graded transition between two materials using a lattice structure.

`lattice_element.py` - Test the min and max dilation values for a single lattice element

`viewer.py` - Load and display a .vf file

![lattice transition example image](../master/lattice_transition/images/lattice-transition-2.png?raw=true)

![lattice transition example print](../master/lattice_transition/images/lattice-transition-2-printed.jpg?raw=true)
