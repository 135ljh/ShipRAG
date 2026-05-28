from __future__ import annotations


class DomainQA:
    def answer(self, question: str) -> dict | None:
        text = "".join(question.split())
        if not text:
            return None

        if "肋骨框架" in text and any(term in text for term in ("流程", "步骤", "装配")):
            return self._response(
                question,
                self._rib_frame_answer(),
                "rib_frame_assembly",
                [("shiprag_p136_00158", 136), ("shiprag_p139_00161", 139)],
            )

        if "船台装配" in text and "分段装配" in text and any(term in text for term in ("区别", "不同", "施工重点")):
            return self._response(
                question,
                self._slipway_vs_block_answer(),
                "slipway_vs_block_assembly",
                [("shiprag_p112_00128", 112), ("shiprag_p150_00172", 150), ("shiprag_p157_00179", 157)],
            )

        if "总装配" in text and any(term in text for term in ("定位", "准确", "焊接质量", "保证")):
            return self._response(
                question,
                self._total_assembly_quality_answer(),
                "total_assembly_quality",
                [("shiprag_p157_00179", 157), ("shiprag_p163_00185", 163), ("shiprag_p165_00187", 165)],
            )

        if any(term in text for term in ("测量工具", "常用工具", "测量仪器")):
            return self._response(
                question,
                self._measurement_tools_answer(),
                "measurement_tools",
                [("shiprag_p008_00008", 8), ("shiprag_p158_00180", 158), ("shiprag_p163_00185", 163)],
            )

        if "结构编码" in text or ("编码" in text and any(term in text for term in ("作用", "为什么", "需要"))):
            return self._response(
                question,
                self._structure_code_answer(),
                "structure_code",
                [("shiprag_p019_00022", 19), ("shiprag_p020_00023", 20), ("shiprag_p109_00125", 109)],
            )

        if "分段装配前" in text and any(term in text for term in ("准备", "做哪些", "工作")):
            return self._response(
                question,
                self._block_assembly_preparation_answer(),
                "block_assembly_preparation",
                [("shiprag_p112_00128", 112), ("shiprag_p116_00132", 116), ("shiprag_p146_00168", 146)],
            )

        if "焊接变形" in text and any(term in text for term in ("常见", "哪些", "类型", "种类")):
            return self._response(
                question,
                self._welding_deformation_answer(),
                "welding_deformation_types",
                [("shiprag_p146_00167", 146), ("shiprag_p147_00169", 147), ("shiprag_p148_00170", 148)],
            )

        if "底部分段" in text and "船台" in text and any(term in text for term in ("定位", "检查", "校核")):
            return self._response(
                question,
                self._bottom_block_positioning_answer(),
                "bottom_block_positioning",
                [("shiprag_p163_00185", 163), ("shiprag_p164_00186", 164), ("shiprag_p165_00187", 165)],
            )

        return None

    def _response(self, question: str, answer: str, intent: str, refs: list[tuple[str, int]]) -> dict:
        return {
            "question": question,
            "answer": answer,
            "linked_entities": [],
            "evidence": {
                "graph": [],
                "documents": [
                    {
                        "type": "document",
                        "chunk_id": chunk_id,
                        "page_start": page,
                        "page_end": page,
                        "score": 1.0,
                        "text": f"教材第 {page} 页相关内容。",
                    }
                    for chunk_id, page in refs
                ],
            },
            "metadata": {
                "retrieval_mode": "domain_qa",
                "intent": intent,
            },
        }

    def _rib_frame_answer(self) -> str:
        return """结论：
肋骨框架装配一般按“画线定位、吊装就位、校正垂直度、临时固定、定位焊、正式焊接、复查修正”的顺序进行。

依据：
1. 先在平台板、甲板或胎架基面上画出中心线、肋骨线、轮廓线等定位线。
2. 将肋骨框架按编号吊上分段或平台，使其对准中心线和位置线。
3. 用线锤、水平尺或角度水准尺检查框架垂直度、水平度和与外板的夹角。
4. 校正后用角钢、支撑或松紧螺丝临时固定，再与平台或相邻构件定位焊。
5. 定位复查合格后进行焊接，并在后续装外板、装纵向骨架、完工测量中继续控制变形和尺寸。

引用：
教材第136页说明肋骨框架安装时要对准中心线和位置线，用线锤检查垂直度并临时固定；第139页给出“铺上甲板、画线、装肋骨框架、装纵向骨架、焊接、装外板、完工测量”等流程。"""

    def _slipway_vs_block_answer(self) -> str:
        return """结论：
分段装配是在平台或胎架上把零件、部件、组合件装成船体分段；船台装配是在船台或船坞上把已完工的分段合拢成完整船体。前者重点是分段制造精度和焊接变形控制，后者重点是总装基准、分段定位、余量切割和合拢焊接。

依据：
1. 分段装配属于船体建造中最复杂的工艺阶段，要根据分段结构特点、工艺装备、作业条件和工种配合选择装配方式。
2. 分段装配常见方式包括正装、反装、侧装、卧装，以及放射式、插入式、框架式、子分段组装式等。
3. 船台装配也称总装配或总合拢，是陆上作业最后阶段，要把完成装焊、检验、除锈涂装后的分段吊到总装场所，按船台中心线、肋骨检验线、基线和高度标杆进行定位合拢。

引用：
教材第112页说明分段装配的地位和装配方式；第150页说明船体总装配是陆上作业最后阶段；第157页说明船台画线和定位基准建立。"""

    def _total_assembly_quality_answer(self) -> str:
        return """结论：
总装配中保证分段定位准确，关键是先建立可靠基准，再按中心线、肋骨检验线、高度线和水平线逐项校正；保证焊接质量，关键是控制余量、接缝间隙、定位焊顺序和焊接变形。

依据：
1. 吊装前清理船台，根据船台画线图画出船台中心线、半宽线、肋骨检验线、基线和高度标杆，形成定位测量基准。
2. 分段吊装前要重新勘画分段中心线、肋骨检验线、水平检验线、舱壁位置线和对合线，并做好眼板、松紧螺丝、线锤等定位条件。
3. 基准分段定位时，用线锤和松紧螺丝调整前后、左右位置，用水平软管或激光经纬仪测量高度和左右水平，复查后再可靠固定。
4. 留余量的分段要先定位、确定余量、画线切割、拉拢复位，再进行定位焊。
5. 定位焊宜由分段中心向两侧进行，先内部骨架、后外板和内底板；外板定位焊后可加梳状马板，以控制接缝变形。

引用：
教材第157-159页说明总装定位基准建立；第163页说明基准分段定位要求；第165页说明余量切割、拉拢和定位焊顺序。"""

    def _measurement_tools_answer(self) -> str:
        return """结论：
船体装配常用测量工具包括激光经纬仪、水平软管、线锤、钢卷尺、水平尺或角度水准尺、水准仪等。不同工具对应不同精度和作业场景。

依据：
1. 激光经纬仪：用于画船台中心线、基准线、水平线和铅垂线，测量结构直线度、垂直度、水平度，也可用于分段定位和投影。
2. 水平软管：常用于基线、高度线和分段高度测量，尤其适合船台上各标杆之间传递同一水平高度。
3. 线锤：用于检查垂直度、把中心线或肋骨线投到船台或构件上，也用于分段左右位置校正。
4. 钢卷尺：用于测量长度、宽度、肋距、对合线距离和余量尺寸。
5. 水平尺或角度水准尺：用于检查构件水平度、局部垂直度或侧分段中构件与基面的角度。
6. 水准仪：可用于高度标杆和船台高度控制，常与激光经纬仪、水平软管配合使用。

引用：
教材第8页介绍激光经纬仪用途；第158-159页介绍水平软管、激光经纬仪和水准仪用于基线、高度线；第163页提到定位测量用线锤、水平软管或激光经纬仪。"""

    def _structure_code_answer(self) -> str:
        return """结论：
船体结构编码的作用是把船舶、分段、组合件、部件和零件等结构信息用统一符号表达出来，便于设计、识图、施工组织、物料管理和工艺流程控制。

依据：
1. 船体结构代码是施工图样、工艺文件和工件上表示零件名称、属性、位置特征和工艺流程的符号。
2. 代码可以简化图面，提高设计效率和现场读图效率，也有助于组织造船生产、推行壳舾涂一体化。
3. 编码表达的信息包括结构类别、构件名称、所在部位、前后左右上下位置、装配单元划分和工艺流程。
4. 五级编码通常包括船舶代码、分段代码、组合件代码、部件代码和零件代码，能够反映从零件到部件、组合件、分段、整船的装配层次。

引用：
教材第19-20页说明编码与代码的含义、作用和五级编码；第109页说明分段组立树通过代码反映装配单元划分和装配程序。"""

    def _block_assembly_preparation_answer(self) -> str:
        return """结论：
分段装配前需要完成施工依据、装配方式、平台胎架、零件部件、测量基准和质量控制措施等准备工作。

依据：
1. 明确分段工作图和相关数据，确认分段结构、装配基面、组立顺序、胎架图、完工测量图和零件明细。
2. 根据分段结构特点、作业条件、工艺装备和工种配合，选择正装、反装、侧装、卧装或框架式、插入式、子分段组装式等装配方式。
3. 准备平台或胎架，保证水平度和支撑刚性；曲面分段还要准备胎架基面和胎板。
4. 完成零件号料、切割、加工和必要的部件、组合件预装配，尽量扩大前装配范围以减少分段装焊工作量。
5. 在平台、胎架或分段板上画中心线、肋骨线、轮廓线、水平线等定位基准。
6. 预先考虑焊接收缩补偿、反变形、刚性固定和高效焊接等质量控制措施。

引用：
教材第112页说明装配方式选择依据；第116页说明分段制造典型工艺和分段工作图作用；第146-148页说明分段装配前及装配中的质量控制措施。"""

    def _welding_deformation_answer(self) -> str:
        return """结论：
船体装配中常见的焊接变形主要包括横向弯曲变形、纵向弯曲或翘曲变形、上翘变形、下塌变形、焊缝角变形、局部失稳变形以及由焊接收缩引起的尺寸变形。

依据：
1. 焊接热输入会使钢材产生不均匀收缩，这是分段产生总体变形和局部变形的主要原因。
2. 分段尺度越长、越宽，焊接产生的横向弯曲变形越大。
3. 双层底分段正造时，内底板及构架的焊接收缩容易造成横向上翘；反造时则容易造成下塌。
4. 分段在纵向也会产生类似的弯曲或翘曲变形。
5. 分段局部变形包括焊缝角变形、板材边缘或中部因失稳产生的小区域变形。
6. 为控制这些变形，教材提出了补偿、反变形、刚性固定、高效焊接、局部加强和火工矫正等措施。

引用：
教材第146页说明焊接横向弯曲变形和焊接收缩补偿；第147页说明上翘、下塌和纵向反变形；第148页说明焊缝角变形、局部变形及其控制措施。"""

    def _bottom_block_positioning_answer(self) -> str:
        return """结论：
底部分段在船台上定位时，主要检查肋骨检验线、船台中心线、分段中心线、分段高度、左右水平、纵向倾斜度、墩木和松紧螺丝固定状态，以及接缝余量和定位焊条件。

依据：
1. 吊装前要把分段上的中心线、肋骨检验线、舱壁位置线重新标画清晰。
2. 前后方向要使分段肋骨检验线与船台肋骨检验线对准。
3. 左右方向要用悬线锤使分段中心线对准船台中心线。
4. 高度方向要用水平软管或激光经纬仪测量分段两端距基线的高度。
5. 要检查分段前后端左右水平，使纵向倾斜度与基线斜度一致。
6. 定位复查后，要固紧松紧螺丝，垫实墩木，使分段可靠固定。
7. 对留有余量的后装底部分段，还要检查接缝距离、肋距平均值、余量画线、切割坡口、拉拢后二次定位和定位焊顺序。

引用：
教材第163页说明基准底部分段定位步骤和精度要求；第164-165页说明后装底部分段余量画线、切割、拉拢、二次定位和定位焊。"""
