import cv2
import math
from matplotlib import pyplot as plt


def get_huMomentun(pol):
    fname = "pol.jpg"
    pol.plot()
    # plt.show()
    plt.savefig(fname)
    plt.close()

    # Read image as grayscale image
    im = cv2.imread(fname, cv2.IMREAD_GRAYSCALE)
    moments = cv2.moments(im)           # Calculate Moments
    huMoments = cv2.HuMoments(moments)  # Calculate Hu Moments
    # Hu Moments have a large range. Some hu[i] are not comparable in magnitude,
    # a log transform brings them in the same range
    i = 0
    for i in range(0, 7):
        huMoments[i] = -1 * \
            math.copysign(1.0, huMoments[i][0]) * \
            math.log10(abs(huMoments[i][0]))
    return ([x.tolist()[0] for x in huMoments])
