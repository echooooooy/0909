# coding:utf-8
from common.stpu import stpu_vpu, stpu_top,stpu_device
from unittest import TestCase, TestSuite, TextTestRunner
from ctypes import *
from common.data.read_yaml import *
from common.media.video import Video
from common.media.ffmpeg import libavcodec

vcfg = yaml_cfg("vpu_cfg.yaml")
ip_addr = vcfg.get_value("ip_addr_invalid").encode()
dev_id = c_uint32(vcfg.get_value("dev_id_invalid"))
media_file = vcfg.get_value("media_file_invalid").encode()
afbc_enable = c_int32(vcfg.get_value("afbc_enable_invalid"))
hist_enable = c_int32(vcfg.get_value("hist_enable_invalid"))
hist_threshold = c_int32(vcfg.get_value("hist_threshold_invalid"))


class Test(TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ip = ip_addr
        self._id = dev_id
        self.v = Video(media_file=media_file)
        self.video_info = self.v.get_media_info()
        self.codec: POINTER(stpu_vpu.StpuCodec) = pointer(stpu_vpu.StpuCodec(0))
        self.param: stpu_vpu.StpuCodecParam = stpu_vpu.StpuCodecParam()

    def init(self, ip: str, id: int):
        print(stpu_vpu.stpuvpuVersion())
        self.assertEqual(stpu_top.stpuHalTopInit(ip.encode()), stpu_top.halSuccess, "HalTopInit Failure")
        self.assertEqual(stpu_vpu.stpuHalLibVpuInit(), stpu_vpu.halSuccess, "HalLibVpuInit Failure")
        self.assertEqual(stpu_vpu.stpuHalVpuOpen(), stpu_vpu.halSuccess, "HalVpuOpen Failure")
        self.assertEqual(stpu_device.stpuHalDeviceOpen(c_uint32(id)), stpu_device.halSuccess, "DeviceOpen Failure")

        self.param.codec_type = stpu_vpu.CODEC_PARAM_VIDEO_DECODER
        self.param.in_pix_fmt = stpu_vpu.CODEC_PIX_FMT_NV12
        self.param.out_pix_fmt = stpu_vpu.CODEC_PIX_FMT_NV12
        self.param.width = self.video_info.get('width')
        self.param.height = self.video_info.get('height')
        self.param.codec_id = libavcodec.AV_CODEC_ID_H264
        self.param.afbc_enable = afbc_enable
        self.param.hist_enable = hist_enable
        self.param.hist_threshold = hist_threshold
        self.assertEqual(stpu_vpu.stpuHalCreateVideoDecoder(pointer(self.param), self._id, pointer(self.codec)),
                         stpu_vpu.halSuccess,
                         "HalCreateVideoDecoder Failure")
        print("init over.")

    def process_frame_cb(self, frame_size: int, frame_data: any) -> bool:
        if frame_size == 0:
            return True
        packet: stpu_vpu.StpuCodecPacket = stpu_vpu.StpuCodecPacket()
        frame: POINTER(stpu_vpu.StpuCodecFrame) = pointer(stpu_vpu.StpuCodecFrame(0))
        print("alloc")
        self.assertEqual(stpu_vpu.stpuHalAllocFrame(pointer(frame)), stpu_vpu.halSuccess, "HalAllocFrame Failure")
        print("alloc over.")
        packet.data = cast(frame_data, POINTER(c_uint8))
        packet.size = frame_size
        print("stpuHalAllocFrame,ret: ")
        ret = stpu_vpu.stpuHalDecodePacket(self.codec, pointer(packet), frame)
        print("stpuHalAllocFrame,ret: ", ret)
        if stpu_vpu.halErrorEAGAIN == ret:
            return True
        elif stpu_vpu.halErrorEOF == ret:
            return False
        elif stpu_vpu.halSuccess != ret:
            return False
        ref_frame: POINTER(stpu_vpu.StpuCodecFrame) = pointer(stpu_vpu.StpuCodecFrame(0))
        # assert stpu_vpu.stpuHalAllocFrame(pointer(ref_frame)) == stpu_vpu.halSuccess
        # assert stpu_vpu.stpuHalRefFrame(frame,ref_frame) == stpu_vpu.halSuccess
        # assert stpu_vpu.stpuHalUnrefFrame(frame) == stpu_vpu.halSuccess
        # assert stpu_vpu.stpuHalFreeFrame(pointer(ref_frame)) == stpu_vpu.halSuccess
        assert stpu_vpu.stpuHalFreeFrame(pointer(frame))
        return True

    def destroy(self):
        assert stpu_vpu.stpuHalDestroyCodec(pointer(self.codec)) == stpu_vpu.halSuccess
        assert stpu_vpu.stpuHalVpuClose() == stpu_vpu.halSuccess
        stpu_top.stpuHalTopDeinit()

    def test_decode(self):
        self.init(self._ip, self._id)
        self.v.get_frame_raw_data(procss_func=self.process_frame_cb)
        self.destroy()



if __name__ == '__main__':
    pass
    # suite = TestSuite()
    # suite.addTest(Test('test_decode'))
    # TextTestRunner().run(suite)
