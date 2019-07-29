# -*- coding: utf-8 -*-
from sentence_parser import *
import re
from collections import Counter
from GraphShow import *
from keywords_textrank import *

'''事件挖掘'''
class CrimeMining:
    def __init__(self):
        self.textranker = TextRank()
        self.parser = LtpParser()
        self.ners = ['nh', 'ni', 'ns']
        self.ner_dict = {
        'nh':'人物',
        'ni':'机构',
        'ns':'地名'
        }
        self.graph_shower = GraphShow()

    '''移除括号内的信息，去除噪声'''
    def remove_noisy(self, content):
        p1 = re.compile(r'（[^）]*）')
        p2 = re.compile(r'\([^\)]*\)')
        return p2.sub('', p1.sub('', content))

    '''收集命名实体'''
    def collect_ners(self, words, postags):
        ners = []
        for index, pos in enumerate(postags):
            if pos in self.ners:
                ners.append(words[index] + '/' + pos)
        return ners

    '''对文章进行分句处理'''
    def seg_content(self, content):
        return [sentence for sentence in re.split(r'[？?！!。；;：:\n\r]', content) if sentence]

    '''对句子进行分词，词性标注处理'''
    def process_sent(self, sent):
        words, postags = self.parser.basic_process(sent)
        return words, postags

    '''构建实体之间的共现关系'''
    def collect_coexist(self, ner_sents, ners):
        co_list = []
        for sent in ner_sents:
            words = [i[0] + '/' + i[1] for i in zip(sent[0], sent[1])]
            co_ners = set(ners).intersection(set(words))
            co_info = self.combination(list(co_ners))
            co_list += co_info
        if not co_list:
            return []
        return {i[0]:i[1] for i in Counter(co_list).most_common()}

    '''列表全排列'''
    def combination(self, a):
        combines = []
        if len(a) == 0:
            return []
        for i in a:
            for j in a:
                if i == j:
                    continue
                combines.append('@'.join([i, j]))
        return combines

    '''抽取出事件三元组'''
    def extract_triples(self, words, postags):
        svo = []
        tuples, child_dict_list = self.parser.parser_main(words, postags)
        for tuple in tuples:
            rel = tuple[-1]
            if rel in ['SBV']:
                sub_wd = tuple[1]
                verb_wd = tuple[3]
                obj = self.complete_VOB(verb_wd, child_dict_list)
                subj = sub_wd
                verb = verb_wd
                if not obj:
                    svo.append([subj, verb])
                else:
                    svo.append([subj, verb+obj])
        return svo

    '''过滤出与命名实体相关的事件三元组'''
    def filter_triples(self, triples, ners):
        ner_triples = []
        for ner in ners:
            for triple in triples:
                if ner in triple:
                    ner_triples.append(triple)
        return ner_triples

    '''根据SBV找VOB'''
    def complete_VOB(self, verb, child_dict_list):
        for child in child_dict_list:
            wd = child[0]
            attr = child[3]
            if wd == verb:
                if 'VOB' not in attr:
                    continue
                vob = attr['VOB'][0]
                obj = vob[1]
                return obj
        return ''

    '''对文章进行关键词挖掘'''
    def extract_keywords(self, words_list):
        return self.textranker.extract_keywords(words_list, 10)

    '''基于文章关键词，建立起实体与关键词之间的关系'''
    def rel_entity_keyword(self, ners, keyword, subsent):
        events = []
        rels = []
        sents = []
        ners = [i.split('/')[0] for i in set(ners)]
        #keyword = [i[0] for i in keyword]
        for sent in subsent:
            tmp = []
            for wd in sent:
                if wd in ners + keyword:
                    tmp.append(wd)
            if len(tmp) > 1:
                sents.append(tmp)
        for ner in ners:
            for sent in sents:
                if ner in sent:
                    tmp = ['->'.join([ner, wd]) for wd in sent if wd in keyword and wd != ner and len(wd) > 1]
                    if tmp:
                        rels += tmp
        for e in set(rels):
            events.append([e.split('->')[0], e.split('->')[1]])
        return events


    '''利用标点符号，将文章进行短句切分处理'''
    def seg_short_content(self, content):
        return [sentence for sentence in re.split(r'[，,？?！!。；;：:\n\r\t ]', content) if sentence]

    '''挖掘主控函数'''
    def main(self, content):
        # 对文章进行去噪处理
        content = self.remove_noisy(content)
        # 对文章进行长句切分处理
        sents = self.seg_content(content)
        # 对文章进行短句切分处理
        subsents = self.seg_short_content(content)
        subsents_seg = []
        # words_list存储整篇文章的词频信息
        words_list = []
        # ner_sents保存具有命名实体的句子
        ner_sents = []
        # ners保存命名实体
        ners = []
        # triples保存主谓宾短语
        triples = []
        # 存储文章事件
        events = []
        
        for sent in subsents:
            words, postags = self.process_sent(sent)
            words_list += [[i[0], i[1]] for i in zip(words, postags)]
            subsents_seg.append([i[0] for i in zip(words, postags)])
            ner = self.collect_ners(words, postags)
            if ner:
                triple = self.extract_triples(words, postags)
                if not triple:
                    continue
                triples += triple
                ners += ner
                ner_sents.append([words, postags])

        # 获取文章关键词, 并图谱组织, 这个可以做
        keywords = [i[0] for i in self.extract_keywords(words_list)]
        
        for keyword in keywords:
            name = keyword
            cate = '关键词'
            events.append([name, cate])
        # 对三元组进行event构建，这个可以做
        for t in triples:
            if (t[0] in keywords or t[1] in keywords) and len(t[0]) > 1 and len(t[1]) > 1:
                events.append([t[0], t[1]])

        # 获取文章词频信息话，并图谱组织，这个可以做
        word_dict = [i for i in Counter([i[0] for i in words_list if i[1][0] in ['n', 'v'] and len(i[0]) > 1]).most_common()][:10]
        for wd in word_dict:
            name = wd[0]
            cate = '高频词'
            events.append([name, cate])

        #　获取全文命名实体，这个可以做
        ner_dict = {i[0]:i[1] for i in Counter(ners).most_common()}
        for ner in ner_dict:
            name = ner.split('/')[0]
            cate = self.ner_dict[ner.split('/')[1]]
            events.append([name, cate])

        # 获取全文命名实体共现信息,构建事件共现网络
        co_dict = self.collect_coexist(ner_sents, list(ner_dict.keys()))
        co_events = [[i.split('@')[0].split('/')[0], i.split('@')[1].split('/')[0]] for i in co_dict]
        events += co_events
        #将关键词与实体进行关系抽取
        events_entity_keyword = self.rel_entity_keyword(ners, keywords, subsents_seg)
        events += events_entity_keyword
        #对事件网络进行图谱化展示
        
        self.graph_shower.create_page(events)
        

content1 = '''
新快报记者从广州警方获悉，2002年1月7日，广州番禺警方接到群众报警，称其朋友卢某（男）于1月6日凌晨失踪。民警随后在番禺区市桥街一出租屋内找到卢某，当时卢某已经死亡，身上财物丢失。案发后没多久，番禺警方就将涉嫌参与抢劫杀害卢某的其中三名嫌疑人耿某、胡某以及翁某（女）抓获归案，另有一名嫌疑人力天佑负案在逃。
据嫌疑人交代，2002年元旦过后，力天佑找到耿某和胡某，告知两人有一个“发财”的机会：力天佑发现卢某很有钱，密谋由翁某将卢某带回翁某租住的出租屋，力天佑等三人伺机进入出租屋抢劫。
案发当天，力天佑带着耿某和胡某先行进入翁某租住的出租屋内等待。晚上22时许，翁某带着卢某回到出租屋，一进入屋内，力天佑等三人合力将卢某推倒在床上，用手捂住卢某嘴巴，用绳索绑住卢某手脚。一番拳打脚踢之后，力天佑从卢某身上搜出两台手机和一个钱包，将其中一台手机给了耿某，又给了胡某一千元钱。眼见卢某因窒息而死，四人逃离了出租屋。
卢某的家人和朋友因为一直无法联系上卢某，多方找寻未果，向番禺警方报警。警方很快将翁某、耿某和胡某三人抓获，但狡猾的力天佑一直潜逃在外。
'''
content2 = '''
正义网白银6月12日电(陈昕)利用农村寺庙疏于管理的漏洞,屡屡偷窃香客捐献的香火钱,结果不慎遗失在寺庙里的身份证“出卖”了他。近日,经甘肃省平川区检察院提起公诉,法院以盗窃罪判处被告人张海永有期徒刑六个月,并处罚金2000元。
　　张海永曾因手头缺钱而去撬自动取款机,结果被行政拘留10日。2015年4月的一天,他来到平川区某村的一座寺庙,趁无人之际撬开殿内放置的功德箱,偷走了100元香火钱。之后,张海永一发不可收拾,2015年4月至2017年1月,先后7次在平川、中卫两地多座庙宇中实施盗窃,共盗走人民币1096元。
　　张海永自认为做得神不知鬼不觉,谁知天网恢恢疏而不漏,他不慎遗失在寺庙里的身份证将嫌疑指向了他。今年1月,张海永被抓获归案。
'''

content3 = '''
女子以开金店为由，将丈夫骗进传销窝点后，拿走手机不知去向。被民警解救后，男子觉得不可思议。近日，咸阳市公安局彩虹分局捣毁一传销窝点，解救被骗群众9人。
　　传销团伙人员构成多为亲戚和朋友
　　9月13日，咸阳市公安局彩虹分局西区派出所民警在日常走访调查中发现，辖区某小区121号楼经常有外地人频繁出入，疑似为一传销窝点。民警经过连日守候，发现涉及人员较多，根据掌握的情况，9月15日上午10时许，彩虹分局西区派出所民警全员出动，立即查处。
　　民警以查电表为名叫开门后，发现这户88平方米的房间里竟然住着7男2女，正在组织学习。他们均为外地口音，分别来自山东、湖南、湖北、广西等地。通过现场检查，证实确为一传销团伙。民警将现场所有人员带回派出所，现场查获收缴笔记本10余本，查获身份证16个。
　　经调查询问，该传销团伙以销售化妆品为名，采取拉人头入伙的方法，骗取亲友加入该团伙。凡拉人入伙购买一份价值2900元的化妆品，上线业务员即得525元，从主管、主任、经理、老总各级都按不同比例和份额“分红”，级别越高分红越多。该组织共骗2名女子和7名男子先后入伙，人员构成多为亲戚和朋友，且不在一处，一个地方人员互不认识，成员不停地处于流动状态，且组成人员具有很强的反侦查意识。
　　学习笔记记录要“敢突破、不要脸”
　　其中有一名湖南籍男子张某，是其妻子以开金店为名将其骗到咸阳，14日晚吃过饭后，妻子将他带至该处后便不知去向，还拿走了他的手机。在民警告知后，该男子感觉到十分震惊和不可思议。
　　民警介绍，在现场查获的学习笔记本上，记录着要以“旅游、找工作、干工程、谈朋友”等为借口，以“电话、书信、面对面和上门邀约”的方式，将“亲人、邻居、同学、同事等有责任心、事业心”的发展对象骗至传销窝点，通过“铺底、摸底、吸引、聊色”等交谈话题，“谈人生、谈理想、谈未来”，做到“敢突破、不要脸”，充满“孤独感、恐惧感、使命感、神秘感”，学会“接受、承受、享受”……“在说不出、解决不了的时候要转移话题…”“行业中正确的方式方法就是骗，骗等于技巧，技巧绝不等于骗…”等字眼，手段卑劣，触目惊心。
'''
content4 = '''
见公益组织设立的捐衣箱挡了自己的“财路”,便多次盗窃旧衣服卖钱。日前,经江西省贵溪市检察院提起公诉,法院以犯盗窃罪判处刘建清拘役五个月,并处罚金1000元。

　　刘建清曾因犯掩饰、隐瞒犯罪所得罪被判处有期徒刑六个月。出狱后,他以收购破烂及旧衣服为生。2016年6月,鹰潭市义工联合会、鹰潭市慈善总会联合发起了“衣旧有爱”公益项目,并联合鹰潭市某再生资源公司在贵溪市四冶生活小区等据点放置了爱心公益捐衣箱。由于设置了公益捐衣箱,刘建清收购衣物的生意受到影响,他便想到偷捐衣箱内衣服卖钱的伎俩。2016年8月至9月期间,刘建清先后三次至贵溪市四冶生活小区,采取破坏公益捐衣箱挂锁的方式,多次将4只捐衣箱内他人捐献的旧衣物全部盗走,后以每斤6角的价格卖给他人,非法获利180元。今年1月20日,刘建清被公安民警抓获。
'''

content5 = '''
正义网镇江9月5日电(通讯员喻瑶 杜希)通过网络二手平台发布虚假信息,利用低廉的价格吸引购买者,诱骗买家先付定金、再付全款,先后诈骗作案11起,涉案金额28200元。2017年7月27日,江苏省句容市人民检察院依法对王明、王晓明两人以涉嫌诈骗罪批准逮捕。
　　妻子患病缺钱治,心思一动起歪念
　　王明和王晓明系父子关系。 2016年2月,王明的妻子胡晓梅患上重病,前期到医院治疗已经花费了十几万元医疗费用,后期治疗更是个“无底洞”,因为家庭生活困难,夫妻二人就动起了诈骗赚钱的歪念。
　　2016年底,王明在湖南娄底路边买了11张外地的手机卡用于联络,又购买了9张通过别人名字的办理的银行卡用于收款,准备好作案工具后,妻子胡晓梅就开始在58同城这些二手交易平台上注册账号,发布各种便宜的虚假二手信息,一切准备就绪,他们静待“猎物”上钩。
　　先后作案11起 先骗定金再骗全款
　　因为胡晓梅在平台上发布的二手信息价格很低,货品质量看起来也不错,所以很快就有“顾客”上门,2017年1月11日,王明接到一个句容宝华人的电话,有意购买他在网络平台上发布的一辆价值3200元的二手车,为了迅速达成交易,王明伪装成卖车老板和买家开始谈价格,价格谈拢后,王明提出要先付定金,再送货上门的要求。当日,王明顺利骗到了100元定金。
　　第二天,王明按照初次双方谈好的送货地址,让自己的儿子王晓明假装成送货人,向被害人打电话,谎称把交易的货物运到了句容市某地,声称自己开的车是“黑车”,直接进行现金交易不太安全,让被害人张某把剩下的购车款打过来,先付钱再拿车,被害人张某立即通过某银行ATM机向王晓明支付了剩余的3100元。王晓明又开始索要其他费用,这时被害人张某已经觉察到了不对劲,不肯再付钱,王晓明就把号码拉黑,不再联系。
　　轻松到手的钱财,进一步引发了父子两人的贪欲。很快,王明的儿子王晓明就不再打工,而是加入父母,全家一起做专职诈骗的“买卖”。随着诈骗次数的增加,他们的诈骗手法也从单纯的收取定金和购车款发展出索要上牌费、安全保证金等多种形式。
　　一家人分工协作,王明负责伪装老板和取钱,王晓明假装送货,胡晓梅发布信息。2017年初至今,王明一家人共诈骗作案11起,涉案金额28200元。
　　受害人报警,父子两人终落法网
　　2017年4月3日,句容市公安局接到了被害人梁某某等人的报警电话,经过公安机关介入侦查,犯罪嫌疑人王明、王晓明于2017年6月6日被抓获归案。2017年7月21日,在句容市检察院检察官在依法对犯罪嫌疑人王明等人讯问过程中,王明在得知自己和儿子因触犯法律而将面临牢狱之灾时,后悔不已。
　　“近年来,检察机关在依法查办的多起诈骗案中发现,不法分子利用可乘之机,以多种方式实施不同的诈骗,作案手段多样化,让广大市民深受其害。检察机关将依法履行职能,对此类诈骗犯罪坚决打击,实现从快从速逮捕和审查起诉,同时检察官提醒广大市民,遇到不法侵害要及时报警。”承办检察官说。
'''
content6 = '''
　　5月7日20时许，昌平警方针对霍营街道某小区一足疗店存在卖淫嫖娼问题的线索，组织便衣警力前往开展侦查。
　　21时14分，民警发现雷某（男，29岁，家住附近）从该足疗店离开，立即跟进，亮明身份对其盘查。雷某试图逃跑，在激烈反抗中咬伤民警，并将民警所持视频拍摄设备打落摔坏，后被控制带上车。行驶中，雷某突然挣脱看管，从车后座窜至前排副驾驶位置，踢踹驾驶员迫使停车，打开车门逃跑，被再次控制。因雷某激烈反抗，为防止其再次脱逃，民警依法给其戴上手铐，并于21时45分带上车。在将雷某带回审查途中，发现其身体不适，情况异常，民警立即将其就近送往昌平区中西医结合医院，22时5分进入急诊救治。雷某经抢救无效于22时55分死亡。
　　当晚，民警在足疗店内将朱某（男，33岁，黑龙江省人）、俞某（女，38岁，安徽省人）、才某（女，26岁，青海省人）、刘某（女，36岁，四川省人）和张某（女，25岁，云南省人）等5名涉嫌违法犯罪人员抓获。经审查并依法提取、检验现场相关物证，证实雷某在足疗店内进行了嫖娼活动并支付200元嫖资。目前，上述人员已被昌平警方依法采取强制措施。
　　为进一步查明雷某死亡原因，征得家属同意后，将依法委托第三方在检察机关监督下进行尸检。
　　男子“涉嫌嫖娼死亡”，家属提多个疑点 要求公开执法记录视频
　　5月7日晚，中国人民大学环境学院2009级硕士研究生雷洋离家后身亡，昌平警方通报称，警方查处足疗店过程中，将“涉嫌嫖娼”的雷某控制并带回审查，此间雷某突然身体不适经抢救无效身亡。
　　面对雷洋的突然死亡，他的家人表示现在只看到了警方的一条官方微博，对于死因其中只有一句“该人突然身体不适”的简单描述，他们希望能够公布执法纪录仪视频，尽快还原真相。
　　由雷洋的同学发布的一份情况说明称，5月7日，由于雷洋夫妇刚得一女，其亲属欲来京探望，航班预计当晚23点30分到达。当晚21时左右，雷洋从家里出门去首都机场迎接亲属，之后雷洋失联。（来源：央视、新京报）

'''

content7 = '''
正文:荣荣出示的一本由涉事医院肿瘤科编制的书，列举滑膜肉瘤在内的42种癌症病人治疗好转的病例。新京报记者李相蓉摄
荣荣出示的一本由涉事医院肿瘤科编制的书，列举滑膜肉瘤在内的42种癌症病人治疗好转的病例。新京报记者李相蓉摄
昨日，武警北京总队第二医院仍然营业。新京报记者王嘉宁摄
原标题：联合调查组进驻百度查“魏则西事件”
新京报讯(记者李丹丹刘夏）昨日，国家互联网信息办公室发言人姜军发表谈话指出，近日“魏则西事件”受到网民广泛关注。根据网民举报，国家网信办会同国家工商总局、国家卫生计生委成立联合调查组进驻百度公司，对此事件及互联网企业依法经营事项进行调查并依法处理。百度对此回应称，欢迎调查组进驻并将全力配合。
国信办、工商总局等联合调查
据悉，联合调查组由国家网信办网络综合协调管理和执法督查局局长范力任组长，国家工商总局广告监管司、国家卫生计生委医政医管局及北京市网信办、工商局、卫生计生委等相关部门共同参加。联合调查组将适时公布调查和处理结果。
习近平总书记4月19日在网络安全与信息化工作座谈会上的讲话强调要增强互联网企业使命感、责任感。习近平强调，办网站的不能一味追求点击率，做搜索的不能仅以给钱的多少作为排位的标准。希望广大互联网企业坚持经济效益和社会效益统一，饮水思源，回报社会，造福人民。
百度三次回应“魏则西”事件
对于国家网信办成立联合调查组，百度公司昨日发布声明，表示欢迎并将全力配合主管部门调查，接受监督。
4月12日，西安电子科技大学21岁学生魏则西因滑膜肉瘤病逝。他去世前在知乎网站撰写治疗经过时称，在百度上搜索出武警某医院的生物免疫疗法，随后在该医院治疗后致病情耽误。此后了解到，该技术在美国已被淘汰。
百度4月28日对此回应称，(魏)则西生前通过电视媒体报道和百度搜索选择的武警北京总队第二医院（下称武警北京二院），百度第一时间进行了搜索结果审查，该医院是一家公立三甲医院，资质齐全。
百度5月1日再次回应网友魏则西病逝事件，称正积极向发证单位及武警总部相关部门递交审查申请函，希望相关部门能高度重视，立即展开调查。
涉事中心停诊有患者要求退钱
昨日，新京报记者从武警北京二院挂号处获悉，该院生物诊疗中心已经停诊，该中心工作人员证实此事，不回应记者任何问题。同时，有此前在该中心进行生物免疫疗法的肿瘤患者来到医院申请退款。医院有便衣安保人员提醒非患者及家属不要靠近门诊及住院楼。
生物诊疗中心昨日停诊
昨日中午，记者来到武警北京二院。院内西侧为6层高的门诊楼，内有外科、内科、肿瘤科、泌尿科等科室。而此次“魏则西”事件涉及的生物诊疗中心，则位于该院东侧的住院楼一层。
记者从该院挂号处了解到，每天上午11点为挂号截止时间，但医院已通知生物诊疗中心于昨日停止挂号，对于为何停诊何时复诊，该人员表示不清楚。
住院部一层北侧的生物诊疗中心分诊台不见护士身影。分诊台左侧即为生物诊疗中心一专家诊室，记者敲门后有护士开门，但表达已停诊后便立刻关门。诊室一旁还有包括细胞室在内的几扇房门，透过细胞室的房门玻璃可看到内有人影，但记者敲门后无人开门。
记者咨询该院急诊科医生及住院楼护士，均表示对生物诊疗中心停诊一事不清楚，并称未听说“魏则西”一事。
有患者获医院退款承诺
今年33岁的荣荣（化名）是一名恶性黑色素瘤患者。今年3月，在深圳打工的她觉得身体不适，去做妇科检查后，被告知患有囊肿。随后荣荣回到湖南常德老家，在当地医院做活检后，被确诊恶性黑色素瘤。
“当时很紧张，就在网上查哪里看这个病好些。”荣荣介绍，4月20日，她通过百度搜索治疗恶性黑色素瘤的办法，发现前几条有推荐医院，并有网络客服人员可以咨询。
“当时不止武警北京二院，有好几家，但我觉得部队上的医院靠谱，检索了一下，还发现它是三甲医院。”荣荣称，她向客服人员咨询后，对方建议她留下姓名及手机号，以方便沟通，并且可以帮忙预约专家。
不久之后，一名自称姚医生的人员打来电话，荣荣向对方表达了自己不想继续化疗的痛苦。“姚医生说，他们医院的生物诊疗中心的技术，是专门针对恶性黑色素瘤的。机器都是从美国进口的。”荣荣表示，热情的姚医生询问何时可以到京，在确定她的火车票时间后，姚医生称，已帮荣荣预约好了4月23日的专家李医生。
“我询问了价格，姚医生在电话里说，先做一个疗程，不住院的话，价格在3.3万左右，住院价格在3.7万元，这与李医生所说的价格一致。”荣荣称，按照预约时间，她在23日上午九点到达医院，没有挂号，直接到达住院楼一层。“到后前面还有五六个人排队，有人是来治疗，也有人来咨询，我等了一个多小时才排到。”见到李医生后，荣荣被安排做了血常规等检查，当天下午2点，医生说她符合生物免疫疗法的治疗方案，付费3万元后，安排她到一个机器前，左右手都扎了一根针头，抽走60ml血液。
荣荣介绍，李医生所采用的方法，是先抽取一部分血液后，进行细胞分离，一周后再将新细胞输回体内。抽完血后，医生并未开其他口服药，“仅叮嘱心态放好。”
荣荣与母亲在附近的出租屋内等待一周后，昨日，母女俩回到医院，准备回输血时，医生却不在，专家诊室房门紧闭。一同等在门外的，还有一位从山东赶来的恶性黑色素瘤患者，该患者从网上看到“魏则西”的报道后，称自己经过两个疗程的治疗并无反应，要求医院返还最后一次检查的一万元费用。最终，医院答应返还该患者7千元，同时返还荣荣2.7万元，由于此前是刷卡付费，医院称15天后会将金额返还至荣荣卡内。
多名患者百度检索经推荐来就诊
同样进行细胞分离治疗的，还有来自北京的宋女士。宋女士介绍，今年3月，在体检中心体检后，发现自己为hpv83阳性（人乳头瘤病毒呈阳性）。在百度检索“hpv”关键词后，点击进入了排在前几位的一个网站。一个客服询问她有什么需要咨询，并称武警北京二院为治疗此方面最专业的医院。
宋女士到医院泌尿科检查后，科室大夫建议她做细胞移植，并称不移植就会得宫颈癌。“我当时都懵了，大夫都建议做细胞移植。”
当天，宋女士进行了包括艾滋、梅毒在内的多项检查，随后医生拿着化验单，建议宋女士做细胞分离。输了3天液，并做了3次光动力治疗后，医院为宋女士做了细胞分离，“两个手上各插一根针，机器嗡嗡响。”宋女士称，细胞分离结束后，医生建议她交20万做细胞移植手术，宋女士不同意，“医生称已经做分离，不继续的话会将已分离的细胞扔掉。”
昨日，记者在该医院8楼住院部见到了患了颜面播散性粟粒狼疮的张女士。张女士脸部起红色疹子已有三年，此前在301、协和等医院治疗过，均未痊愈。前几日，她通过百度检索后，留下姓名电话，随后有客服人员打电话，说建议来武警北京二院检查，不然会越来越严重。
客服人员替张女士预约专家号后，5月1日，张女士来到医院检查。“我刚来，他们让我做了血液和彩超等检查后，就说我这个病严重，要立马住院。”张女士称，交了三千押金后，医生建议她去医院外的药店买一种治疗此病的软膏，此后截至昨日下午，再没有进行其他治疗。住院后在网络上看到“魏则西”事件后，很担心自己也遇到医托，心里很慌。新京报记者李相蓉
病例集称治疗后大多好转
荣荣介绍，除了检查外，医院还给了她一本名为“肿瘤生物技术病例集”的书，有一百多页厚，封面显示主编为李志亮、温洪泽、郭跃生三名医生。
媒体报道称，魏则西父亲受访时表示主治医师为李志亮，护士称李志亮已于去年退休。但院方未向新京报记者证实此消息。
记者注意到，该病例集封面的宣传语为“治疗肿瘤，我们倡导绿色疗法。”内容除了生物治疗的概念、作用流程等内容的介绍外，还列有白血病、唇癌、胆囊癌、肺癌等42种癌症病人的治疗案例，其中包括魏则西所患的滑膜肉瘤。案例内容包括患者的性别、名字，诊断、患病主因、遗传史、病情介绍，并用表格列出患者治疗前后情况比较。记者发现，病例多为积极案例，患者在治疗后病情得到改善，但没有姓名及其他信息，内容真实与否难以考证。新京报记者李相蓉
涉事医院资质如何
百度出具相关许可仍在有效期内
北京市预约挂号统一平台显示，中国人民武装警察部队北京市总队第二医院成立于2000年，是一所三级甲等综合性医院，是北京市首批基本医疗保险定点医院、北京大学人民医院医疗集团成员，国际紧急救援中心网络医院。
根据百度推广官微提供的武警北京二院的许可证显示，其文件全称为“武警部队单位对外有偿服务许可证”。说明显示，此许可证为武警部队单位开具对外有偿服务的合格凭证，并盖有“中国人民武装警察部队后勤部”的章，有效期从2014年1月1日到2017年12月31日。其中，有偿服务范围为“门诊、住院、体检、出（会）诊及专业技术培训。”
此前有媒体报道，涉事诊疗中心系外包给一民营机构。昨日，记者询问该医院多科室医生护士生物诊疗中心是否外包给“莆田系”医院，对方均表示不清楚此事。
媒体报道称，“中国人民武装警察部队北京市总队第二医院”在百度信誉档案中的网址为www.wjmnwk.com。新京报记者通过域名查询，发现联系人为“jijing”，注册时间为2008年。通过邮箱反查发现，该邮箱共注册67个网站域名，最近一次为今年3月份，但网站已无法打开。随后，记者输入其他域名，发现网站已大多无法打开，打开的网站则显示为“贵州368医院妇科诊疗中心”。新京报记者李相蓉信娜
免疫治疗中心有多少
全国多家医院均有涉及，资质难核查
新京报记者查询百度发现，国内多家医院均开展肿瘤生物免疫治疗，如解放军301医院、解放军307医院等。
以解放军301医院为例，其肿瘤生物免疫治疗主要由医院生物治疗科承担。根据官网介绍，科室成立于2012年，年收治肿瘤患者量近1500人。其官网表示，“对肿瘤患者而言，单纯细胞输注治疗多数情况下很难客观评价其疗效，需要多学科为基础联合治疗”。此外，其还标明，生物治疗科针对不同类型肿瘤患者设计制定，并系统性实施包括化疗在内的肿瘤综合治疗。
另一家全名为“解放军307医院CTC肿瘤生物治疗中心”，截至昨日下午18点，其官网已显示无法打开。
根据注册邮箱，记者共反查到37个相同注册邮箱的网站域名，最近一次的注册时间为2014年3月。此外，通过域名查询几家网站后，显示为“黑龙江维多利亚妇产医院”、“阳光妇产医院”、“欧非医疗美容”等。
新京报记者注意到，多家民营医院也打着公立的旗号成立细胞诊疗中心。部分诊疗中心也是用细胞免疫方法治疗肿瘤。
陕西生物细胞诊疗中心正是其中之一。网站介绍，该中心是公立三甲医院。
记者在卫计委医院查询系统（收录各地有二级三级资质的公立医院）输入“陕西生物细胞诊疗中心”，页面显示“没有符合信息”。另一家名为“安徽合肥济民肿瘤医院”也包含生物治疗中心，官网介绍，该肿瘤医院为经安徽省卫生厅批准执业的非营利性三级肿瘤专科医院，该医院同样查询无果。新京报记者信娜
医院和百度担何责
律师称医院主责；百度是否涉虚假广告待查
对于此次事件中的三方责任问题，北京大悦律师事务所合伙人、律师郎克宇认为，武警北京二院应负有主要责任，百度推广负次要责任。如果涉事诊疗中心系外包给了民营机构，那么院方可以对该民营机构追责。
郎克宇表示，即使该科室是承包出去的，武警北京二院也是有审核责任，患者出现问题第一责任还是在医院。“因为病人对承包事宜并不知情。如果是民营机构欺骗了武警医院，医院发现其中有虚假行为，医院可以追责。”
对百度推广的界定，全国政协委员、著名律师施杰和郎克宇均表示，根据新广告法的相关规定，百度推广也属于广告发布的主体，其性质属于有偿服务。
“不像是在一些论坛上发布产品或信息，百度推广本身是一种经营行为，它接受广告主的委托，通过特定平台发布广告信息，且一般是根据费用多少来决定推广信息的排名，因此百度推广属于新广告法的监管范围，工商部门有相应的监管职责。但在整个事件中应负有次要责任。”
关于百度推广发布的此条医疗信息是否涉嫌虚假广告，施杰表示，是否属于虚假广告，要看发布主体发布的内容是否属实，这需要公安部门调查核实，调查其是否有夸大疗效、虚假事实、诱导等情形。同时，工商、卫生部门也要进行认定，看是否符合广告法规定的虚假广告的范畴。
如果认定后确实存在违反法律规定的情形，按照新广告法的规定，需要承担相应责任。如果构成虚假行为，广告经营者、发布者、代言人，都要承担民事、行政，甚至刑事责任。新京报记者李婷婷
魏则西事件始末
●2014年4月
魏则西检查出滑膜肉瘤。一种恶性软组织肿瘤，五年生存率是20%-50%。当时他在西安电子科技大学读大二。
●2015年8月
魏则西在知乎上发帖提问：“二十一岁癌症晚期，自杀是否是更好的选择？”那时候，他做完4次在武警北京二院的生物免疫疗法，没有达到预期效果。这个疗法曾被他和父母视为救命稻草。
●2016年2月
知乎上有人提问：“你认为人性最大的‘恶’是什么？”魏则西将＋这根“救命稻草”的故事作为回答。医院，是在百度上搜的，排名领先。疗法“说得特别好”。他在文中还提到，当时武警北京二院的医生曾经对他说该院与国外大学合作，“有效率达到百分之八九十，看着我的报告单，给我爸妈说保我20年没问题”。结果却被网友告知生物免疫疗法是被国外临床淘汰的技术。
●2016年4月12日
魏则西去世。当天，在一则“魏则西怎么样了？”的知乎帖下，魏则西父亲用魏则西的知乎账号回复称：“我是魏则西的父亲魏海全，则西今天早上八点十七分去世，我和他妈妈谢谢广大知友对则西的关爱，希望大家关爱生命，热爱生活。”
●4月28日
针对自媒体曝出“魏则西”之死事件存在的涉事医院外包诊所给民营机构，百度竞价排名等问题，百度回应称，(魏)则西生前通过电视媒体报道和百度搜索选择的武警北京二院，百度第一时间进行了搜索结果审查，该医院是一家公立三甲医院，资质齐全。
●5月1日
百度再次回应称，针对网友对魏则西所选择的武警北京二院的治疗效果及其内部管理问题的质疑，百度正积极向发证单位及武警总部主管该院的相关部门递交审查申请函，希望相关部门能高度重视，立即展开调查。
'''
content8 = '''
（原标题：中科院研究生遇害案：凶手系同乡学霸，老师同学已为死者发起捐款）

6月14日下午6点多，中科院信息工程研究所硕士研究生谢雕在饭馆招待自重庆远道而来的高中同学周凯旋时，被周凯旋用匕首杀害。随后，周凯旋被北京警方抓获。

周凯旋被抓后，他的家人向被警方递交了精神鉴定材料，称周凯旋患有精神性疾病。

谢雕的家人罗发明告诉南都记者，谢雕被害后，他的研究生老师和同学发起了捐款。并说，谢雕的遗体已经进行尸检，等尸检结果出来后，家人将会把火化后的骨灰带回老家安葬，之后，他们将等待北京检察机关的公诉。

高中同学千里赴京去杀人

今年25岁的谢雕生长于重庆垫江县的一个小山村，谢雕和周凯旋同在垫江中学读高中，两人学习成绩名列前茅，周凯旋经常考年级第一，两人都是垫江中学的优秀毕业生，谢雕考上了西安电子科技大学，周凯旋考取了四川大学。

微信图片_20180627174901_副本.jpg案发现场的行凶者周凯旋（受访者提供）。

学习优秀的周凯旋认为自己应该能考上北大清华等名校，于是在入读四川大学两三个月后，选择了退学复读。经过半年多的苦读，周凯旋以优异成绩考取了西安交通大学，来到了谢雕所在的城市，且是硕博连读。

但周凯旋因大学本科期间因沉迷游戏，考试不及格，最终失掉了硕博连读的机会，本科毕业后就回到重庆寻找就业机会。谢雕自西安电子科技大学毕业后，在2016年考取了中国科学院大学的硕士研究生，所读专业隶属于中科院信息工程研究所。

谢雕的家人告诉南都记者，6月14日下午6点，谢雕在西五环外的中科院信息工程研究所门口见到了久未见面的高中同学周凯旋。把他带到旁边的饭馆吃饭，两人还合影发到了高中同学微信群。这时，谢雕还没意识到周凯旋即将对他带来致命伤害。

南都记者在谢雕遇害现场视频中看到，在谢雕点菜时，周凯旋用匕首刺向他胸部，谢雕中刀站起后退时，周凯旋用匕首又刺向他颈部，谢雕倒地后，周凯旋又从背部向他连刺几刀。之后，又持刀割断了谢雕的颈部动脉。这时，有食客拿起椅子砸向正在行凶的周凯旋。刺死谢雕后，周凯旋举起双手挥舞，随后扬长而去。后来，周凯旋被北京警方抓获。

同学聚会时自己觉得受伤害起杀心

罗发明告诉南都记者，作为被害人家属，他们向北京警方了解到，凶案原因来自两年前的一场同学聚会，谢雕的一些话对周凯旋带来很大心理压力，让他不能释怀。

两年前的一次高中同学聚会中，大家聊的话题很多，也聊到了周凯旋喜欢打游戏的事情，谢雕说了一些激励周凯旋的话，让他不要再打游戏，要振作起来。在参与聚会的同学们看来，这些话是常理之中的，但在周凯旋看来，对他带来很大伤害，两年来给他带来很大心理压力。

参与那次聚会的同学后来回忆，在一起玩“狼人杀”游戏时，谢雕、周凯旋发生了争执，但不愉快的瞬间很快就过去了，大家也都没当回事。

那次聚会之后的春节，不少同学发现被周凯旋拉黑，中断了联系。直至一年之后，周凯旋才加入了高中同学微信群。

谢雕的家人说，周凯旋在网上购买了杀人凶器匕首，收货地址填写了北京，他在北京拿到网购的匕首后，才暗藏在身前来面见谢雕。

师生捐款助他家人渡难关

周凯旋被北京警方抓获后，他的家人向警方称周凯旋患有精神病，并提供了一些证明材料，希望得到从轻处置。


谢雕遇害后，他的学校为失去这么优秀的学生感到惋惜。谢雕的老师说，“谢雕家境并不富裕，本科尚有2.5万助学贷款未偿还，前不久还向同学借款1万，父亲也患有鼻咽癌。”

谢雕的老师和同学发起了捐款，希望能帮助谢雕的家人暂时渡过难关。

谢雕的家人告诉南都记者，他们向谢雕的学校提出要求，希望案件能尽快解决。

罗发明对南都记者说，谢雕的遗体已经进行尸检，尸检后十天至十五天出来结果，等拿到尸检报告后，他们会尽快火化谢雕的遗体，把他的骨灰带回重庆老家安葬。

对于这一案件，谢雕的家人告诉南都记者，他们将等待北京的检察机关提起公诉。


'''
handler = CrimeMining()
handler.main(content8)
