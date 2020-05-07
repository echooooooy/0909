# coding:utf-8
from common.stpu import stpu_vpu,stpu_top
from unittest import TestCase
from ctypes import *
from common.media.video import  Video
from common.media.ffmpeg import libavcodec


class Test(TestCase):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self._ip = "TCP:192.168.1.13:9000"
        self._id = 0
        self.v = Video(media_file="/home/jpfc.mp4")
        self.vidoe_info = self.v.get_media_info()
        self.codec:POINTER(stpu_vpu.StpuCodec) = stpu_vpu.StpuCodec(0)
        self.param:stpu_vpu.StpuCodecParam = stpu_vpu.StpuCodecParam()

    def init(self):
        assert stpu_top.stpuHalTopInit(self._ip) == stpu_top.halSuccess
        assert stpu_vpu.stpuHalLibVpuInit() == stpu_vpu.halSuccess
        assert stpu_vpu.stpuHalVpuOpen(self._id) == stpu_vpu.halSuccess

        self.param.codec_type = stpu_vpu.CODEC_PARAM_VIDEO_DECODER
        self.param.in_pix_fmt = stpu_vpu.CODEC_PIX_FMT_NV12
        self.param.out_pix_fmt = stpu_vpu.CODEC_PIX_FMT_NV12
        self.param.width = self.vidoe_info.get('width')
        self.param.height = self.vidoe_info.get('height')
        self.param.codec_id = libavcodec.AV_CODEC_ID_H264
        self.param.afbc_enable = 1
        self.param.hist_enable = 0
        self.param.hist_threshold = 256

        assert stpu_vpu.stpuHalCreateVideoDecoder(pointer(self.param),self._id,pointer(self.codec)) == stpu_vpu.halSuccess

    def process_frame_cb(self,frame_size:int,frame_data)->bool:
        if frame_size == 0:
            return True
        packet:stpu_vpu.StpuCodecPacket = stpu_vpu.StpuCodecPacket()
        frame:POINTER(stpu_vpu.StpuCodecFrame) = pointer(stpu_vpu.StpuCodecFrame(0))
        assert stpu_vpu.stpuHalAllocFrame(pointer(frame))== stpu_vpu.halSuccess
        packet.data = cast(frame_data,POINTER(c_uint8))
        packet.size = frame_size
        assert stpu_vpu.stpuHalPushPacket(self.codec,pointer(packet)) == stpu_vpu.halSuccess
        while True:
            if stpu_vpu.halSuccess != stpu_vpu.stpuHalPushPacket(self.codec,pointer(packet)):
                break
        ref_frame:POINTER(stpu_vpu.StpuCodecFrame) = pointer(stpu_vpu.StpuCodecFrame(0))
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

    def test_afbs_decode(self):
        self.skipTest("not imp")
        self.init()
        self.v.get_frame_raw_data(procss_func=self.process_frame_cb)
        self.destroy()

    def test_no_afbs_decode(self):
        self.skipTest("not imp")
        self.init()
        self.param.afbc_enable = 1
        self.v.get_frame_raw_data(procss_func=self.process_frame_cb)
        self.destroy()

