"""CEO supervised TikTok-reference → scripts → compliance → AI-video handoff.

Research uses ONLY owner supplied observations/links; no TikTok video is
downloaded, watched or transcribed. Video room receives storyboards and
production prompts, not an auto-generated MP4.
"""
import json
import product_video_workflow as pv
import agent_forum


def process(db_path,task,chat,record_step,update_report,finish):
    mid=task["id"]
    brief=pv.get_brief(db_path,mid)
    facts=pv.summary(brief)
    req="Nhiệm vụ: "+task["title"]+"\nYêu cầu CEO: "+task["detail"]+"\n"+facts
    update_report(db_path,mid,plan="Phòng TikTok → Biên kịch → Kiểm duyệt → Phòng Video AI",error="")
    try:
        agent_forum.record(db_path,mid,"ceo","research","assignment",
            "Phòng nghiên cứu TikTok: phân tích link và ghi chú do chủ giao, chưa trực tiếp xem video.")
        record_step(db_path,mid,"research","in_progress")
        research=chat("research",
            "PHÒNG NGHIÊN CỨU TIKTOK: phân tích các URL do chủ cung cấp như tài liệu tham chiếu, "
            "chỉ rút kết luận từ ghi chú/transcript thực sự cung cấp. Tuyệt đối KHÔNG nhận "
            "đã xem video TikTok, không bịa view/doanh số/review. "
            "Đưa ra bảng URL + mức độ xác minh; phân tích hook/cấu trúc nếu ghi chú có dữ liệu; "
            "đề xuất 3 hướng nội dung nguyên bản, tránh sao chép nguyên bản video khác.\n"+req)
        if not str(research or "").strip():raise RuntimeError("Nghiên cứu TikTok chưa có kết quả")
        pv.stage(db_path,mid,"research",research,"research_complete")
        record_step(db_path,mid,"research","done",result=research)
        agent_forum.record(db_path,mid,"research","ceo","proposal",research)
        agent_forum.record(db_path,mid,"ceo","creative","assignment",
                           "Phòng biên kịch: viết kịch bản gốc, không sao chép nội dung video người khác.")
        record_step(db_path,mid,"creative","in_progress")
        script=chat("creative",
            "PHÒNG BIÊN KỊCH VIDEO BÁN HÀNG: Tạo 2 phương án kịch bản tiếng Việt "
            "cho TikTok, mỗi phương án 5 cảnh × khoảng 8 giây, hook 3 giây đầu, "
            "lời thoại/voice-over, hành động, CTA trung thực. "
            "Không nhận công dụng chữa bệnh, cải thiện bệnh lý, kết quả hoặc giấy chứng nhận "
            "khi chưa có chứng cứ được xác minh. Chữ 'hỗ trợ' không thay thế được chứng cứ. "
            "Không sửa thiết kế chữ/nhãn trên ảnh sản phẩm gốc.\n"+req+
            "\nPHÂN TÍCH NGHIÊN CỨU:\n"+str(research)[:9000])
        if not str(script or "").strip():raise RuntimeError("Phòng biên kịch không trả kịch bản")
        pv.stage(db_path,mid,"script",script,"script_complete")
        record_step(db_path,mid,"creative","done",result=script)
        agent_forum.record(db_path,mid,"creative","ceo","proposal",script)
        agent_forum.record(db_path,mid,"ceo","compliance","assignment",
                           "Kiểm tra công bố sản phẩm và tuyên bố quảng cáo trước khi bàn giao video.")
        record_step(db_path,mid,"compliance","in_progress")
        verdict=chat("compliance",
            "PHÒNG KIỂM DUYỆT: Rà soát tất cả kịch bản, nhãn và giấy công bố nếu có. "
            "PDF trích chữ chưa phải bằng chứng cơ quan chức năng chấp thuận. "
            "Tuyệt đối chặn tuyên bố y tế/chứng nhận chưa được xác minh. "
            "Trả DUY NHẤT JSON: "
            '{"status":"approved","reason":"nội dung an toàn","required_changes":[]} '
            'hoặc {"status":"needs_review","reason":"...","required_changes":["..."]}. '
            "Chỉ approved khi an toàn trên thông tin hiện có.\n"+req+
            "\nKỊCH BẢN:\n"+str(script)[:12500])
        if not str(verdict or "").strip():raise RuntimeError("Phòng kiểm duyệt không trả đánh giá")
        approved=pv.compliance_ok(verdict)
        pv.stage(db_path,mid,"compliance",verdict,"script_complete" if approved else "needs_review")
        record_step(db_path,mid,"compliance","done",result=verdict)
        agent_forum.record(db_path,mid,"compliance","ceo","proposal",verdict)
        if not approved:
            report=("CHƯA BÀN GIAO VIDEO: nội dung cần sửa/kiểm duyệt trước khi sản xuất.\n"+
                    str(verdict)[:5000])
            agent_forum.record(db_path,mid,"ceo","ceo","decision",report)
            update_report(db_path,mid,report=report,error="",plan="Cần rà soát kịch bản và giấy công bố")
            finish(db_path,mid,"done")
            return
        agent_forum.record(db_path,mid,"ceo","creative","assignment",
                           "Phòng Video AI: nhận kịch bản đã kiểm duyệt, chuẩn bị storyboard, không render MP4.")
        storyboard=chat("creative",
            "PHÒNG SẢN XUẤT VIDEO AI: tạo gói tiền kỳ với 5 cảnh × 8 giây, "
            "mỗi cảnh có prompt video, bố cục, chuyển cảnh, thoại, nhạc và phụ đề. "
            "Sản phẩm 3D đã upload chỉ là tệp tham chiếu, không được đổi bao bì/nhãn gốc. "
            "Ghi rõ chưa render MP4 và cần chủ doanh nghiệp duyệt trước phát hành.\n"+
            req+"\nKỊCH BẢN ĐÃ KIỂM DUYỆT:\n"+str(script)[:11500])
        if not str(storyboard or "").strip():
            raise RuntimeError("Phòng Video AI không tạo được gói storyboard")
        pv.stage(db_path,mid,"storyboard",storyboard,"awaiting_video_render")
        agent_forum.record(db_path,mid,"creative","ceo","proposal",
            "Phòng Video AI đã nhận kịch bản; gói storyboard sẵn sàng chờ công cụ render.\n"+
            str(storyboard)[:4000])
        decision=chat("ceo",
            "Bạn là AI CEO. Chốt phương án NỘI BỘ và báo cáo tiếng Việt cho chủ: "
            "phần nghiên cứu là suy luận từ link/ghi chú do chủ cung cấp, không tự xem video; "
            "kịch bản đã chuyển Phòng Video AI thành storyboard, chưa có file MP4. "
            "Cần duyệt cuối trước khi render/xuất bản.\n"+
            req+"\nKIỂM DUYỆT:\n"+str(verdict)[:3500]+
            "\nSTORYBOARD:\n"+str(storyboard)[:8000])
        if not str(decision or "").strip():raise RuntimeError("CEO chưa trả báo cáo")
        agent_forum.record(db_path,mid,"ceo","ceo","decision",decision)
        update_report(db_path,mid,report=decision,error="",
                      plan="Đã bàn giao Phòng Video AI; storyboard sẵn sàng, chưa render MP4")
        finish(db_path,mid,"done")
    except Exception:
        pv.state(db_path,mid,"blocked")
        raise
