from plasmapy.physics import drifts
import astropy.units as u
from astropy.tests.helper import assert_quantity_allclose

class Test_ExB_drift:
    def test_E_x_B_1d_arrays(self):
        E = u.Quantity([1,0,0], unit=u.V/u.m)
        B = u.Quantity([0,1,0], unit=u.T)
        result = drifts.ExB_drift(2*E, 3*B)
        assert_quantity_allclose(result, (2/3)*u.Quantity([0,0,1], u.m/u.s))

    def test_ExB_2d_array(self):
        E = u.Quantity([[1,0,0],
                        [1,0,0],
                        [1,0,0]], unit=u.V/u.m)
        B = u.Quantity([[0,1,0],
                        [0,1,0],
                        [0,1,0]], unit=u.T)

        result = drifts.ExB_drift(2*E, 3*B)
        assert_quantity_allclose(result, (2/3)*u.Quantity([[0,0,1],
                                                           [0,0,1],
                                                           [0,0,1],
                                                           ], unit=u.m/u.s))

    def test_ExB_3d_array(self):
        E = u.Quantity([[[1,0,0]]], unit=u.V/u.m)
        B = u.Quantity([[[0,1,0]]], unit=u.T)

        result = drifts.ExB_drift(2*E, 3*B)
        assert_quantity_allclose(result, (2/3)*u.Quantity([[[0,0,1]]],
                                                          unit=u.m/u.s))
