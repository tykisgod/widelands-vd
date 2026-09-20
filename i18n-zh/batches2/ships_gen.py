"""按既有惯例翻译船名：专名音译、有实义的意译，统一加「号」。"""
import json
import os
import sys

sys.path.insert(0, 'i18n-zh')
sys.path.insert(0, 'C:/Users/ASUS/.claude/skills/localizing-gettext-projects/scripts')
from check_po import parse_po
from batch import key_of

# 亚马逊流域河流名 —— 音译
RIVERS = {
    'Acari': '阿卡里', 'Acre': '阿克里', 'Açuã': '阿苏安', 'Acurauá': '阿库拉瓦',
    'Aiari': '艾阿里', 'Alalaú': '阿拉劳', 'Amanã': '阿马南', 'Amapá': '阿马帕',
    'Andirá': '安迪拉', 'Antimary': '安蒂马里', 'Apoquitaua': '阿波基塔瓦',
    'Apuaú': '阿普阿乌', 'Araçá': '阿拉萨', 'Arara': '阿拉拉', 'Ararirá': '阿拉里拉',
    'Arauã': '阿拉万', 'Aripuanã': '阿里普安南', 'Arrojo': '阿罗霍',
    'Atiparaná': '阿蒂帕拉纳', 'Atucatiquini': '阿图卡蒂基尼',
    'Autaz-mirim': '奥塔斯米林', 'Badajós': '巴达若斯', 'Bararati': '巴拉拉蒂',
    'Biá': '比亚', 'Camaiú': '卡迈乌', 'Camanaú': '卡马瑙', 'Canumã': '卡努曼',
    'Capucapu': '卡普卡普', 'Carabinani': '卡拉比纳尼', 'Cauaburi': '考阿布里',
    'Caurés': '考雷斯', 'Ciriquiri': '西里基里', 'Coari': '科阿里',
    'Copatana': '科帕塔纳', 'Coti': '科蒂', 'Cubate': '库巴特', 'Cuiari': '奎阿里',
    'Cuieiras': '奎埃拉斯', 'Cuini': '奎尼', 'Cuniuá': '库尼瓦',
    'Curicuriari': '库里库里阿里', 'Curiuaú': '库里瓦乌', 'Curuçá': '库鲁萨',
    'Curuduri': '库鲁杜里', 'Curuquetê': '库鲁凯特', 'Daraá': '达拉阿',
    'Demini': '德米尼', 'Eiru': '埃鲁', 'Endimari': '恩迪马里', 'Envira': '恩维拉',
    'Gregório': '格雷戈里奥', 'Guaribe': '瓜里贝', 'Iá': '亚', 'Iaco': '亚科',
    'Içá': '伊萨', 'Içana': '伊萨纳', 'Igapó-Açu': '伊加波阿苏',
    'Inauini': '伊瑙伊尼', 'Ipixuna': '伊皮舒纳', 'Itanhauá': '伊塔尼奥阿',
    'Itaparaná': '伊塔帕拉纳', 'Itaquai': '伊塔夸伊', 'Itucumã': '伊图库曼',
    'Ituí': '伊图伊', 'Ituxi': '伊图希', 'Jacaré': '雅卡雷', 'Jamicia': '雅米西亚',
    'Jandiatuba': '雅恩迪亚图巴', 'Japurá': '雅普拉', 'Jaquirana': '雅基拉纳',
    'Jari': '雅里', 'Jatapu': '雅塔普', 'Jatuarana': '雅图阿拉纳', 'Jaú': '雅乌',
    'Jauaperi': '雅瓦佩里', 'Javary': '雅瓦里', 'Juami': '胡阿米', 'Jufari': '胡法里',
    'Juma': '胡马', 'Juruá': '胡鲁阿', 'Juruena': '胡鲁埃纳', 'Jurupari': '胡鲁帕里',
    'Jutai': '胡泰', 'Jutaizinho': '胡泰津霍', 'Luna': '卢纳', 'Maiá': '迈亚',
    'Maici': '迈西', 'Mamiá': '马米亚', 'Mamoriá': '马莫里亚', 'Mamuru': '马穆鲁',
    'Manacapuru': '马纳卡普鲁', 'Manicoré': '马尼科雷',
    'Manicorezinho': '马尼科雷津霍', 'Mapari': '马帕里', 'Mapiá': '马皮亚',
    'Maracanã': '马拉卡南', 'Marari': '马拉里', 'Marauiá': '马拉维亚',
    'Marié': '马里埃', 'Mariepauá': '马里埃帕瓦', 'Marimari': '马里马里',
    'Mataurá': '马陶拉', 'Matupiri': '马图皮里', 'Maués Açu': '毛埃斯阿苏',
    'Mineruázinho': '米内鲁阿津霍', 'Muaco': '穆阿科', 'Mucum': '穆库姆',
    'Mutum': '穆图姆', 'Nhamundá': '尼亚蒙达', 'Paciá': '帕西亚',
    'Padauari': '帕道阿里', 'Papagaio': '帕帕盖奥', 'Papuri': '帕普里',
    'Paraconi': '帕拉科尼', 'Parauari': '帕拉瓦里', 'Pardo': '帕尔多',
    'Pati': '帕蒂', 'Pauini': '帕乌伊尼', 'Pinhuã': '皮尼安', 'Piorini': '皮奥里尼',
    'Piratucu': '皮拉图库', 'Pitinga': '皮廷加', 'Preto': '普雷图',
    'Puduari': '普杜阿里', 'Pureté': '普雷特', 'Puruê': '普鲁埃', 'Purus': '普鲁斯',
    'Quixito': '基希托', 'Sepatini': '塞帕蒂尼', 'Sepoti': '塞波蒂',
    'Seruini': '塞鲁伊尼', 'Sucunduri': '苏昆杜里', 'Tapajós': '塔帕若斯',
    'Tapauá': '塔帕瓦', 'Tarauacá': '塔劳阿卡', 'Tarumã Açu': '塔鲁曼阿苏',
    'Tarumã Mirim': '塔鲁曼米林', 'Tea': '特亚', 'Tefé': '特费',
    'Tonantins': '托南廷斯', 'Toototobi': '托托托比', 'Traíra': '特拉伊拉',
    'Tumiã': '图米安', 'Tupana': '图帕纳', 'Uaicurapa': '瓦伊库拉帕',
    'Uarini': '瓦里尼', 'Uatumã': '瓦图曼', 'Uaupés': '瓦乌佩斯', 'Umari': '乌马里',
    'Uneiuxi': '乌内尤希', 'Unini': '乌尼尼', 'Uruá': '乌鲁阿',
    'Urubaxi': '乌鲁巴希', 'Urubu': '乌鲁布', 'Urucu': '乌鲁库',
    'Urupadi': '乌鲁帕迪', 'Xeruã': '谢鲁安', 'Xie': '希埃',
}

# 印加神祇、君主与圣地 —— 音译
INCA = {
    'Apu': '阿普', 'Illapu': '伊利亚普', 'Apu Illapu': '阿普伊利亚普', 'Ayar Cachi': '阿亚尔卡奇',
    'Illapa': '伊利亚帕', 'Inti': '因蒂', 'Kuychi': '库伊奇',
    'Mama Killa': '玛玛基利亚', 'Mama Occlo': '玛玛奥克略',
    'Manco Cápac': '曼科卡帕克', 'Pachamama': '帕查玛玛',
    'Quchamama': '库查玛玛', 'Sachamama': '萨查玛玛', 'Viracocha': '维拉科查',
    'Yakumama': '亚库玛玛', 'Atahuallpa': '阿塔瓦尔帕',
    'Lloqe Yupanki': '略克尤潘基', 'Manqo Qhapaq': '曼科卡帕克',
    'Mayta Qhapaq': '迈塔卡帕克', 'Pachakuti': '帕查库提',
    'Qhapaq Yupanki': '卡帕克尤潘基', 'Thupa': '图帕', 'Urqon': '乌尔孔',
    'Washkar': '瓦斯卡尔', 'Wayna Qhapaq': '瓦伊纳卡帕克',
    'Yawar Waqaq': '亚瓦尔瓦卡克', 'Zinchi Roqa': '辛奇罗卡',
    'Lake Titicaca': '的的喀喀湖', 'Koricancha': '科里坎查',
}

# 有实义的词按义译；罗马人名、火山名音译
MEANING = {
    'Bison': '野牛', 'Eagle': '雄鹰', 'Hakhor': '哈霍尔', 'Valkyrie': '女武神',
    'Wisent': '欧洲野牛',
    'Adamas': '金刚石', 'Agrippa': '阿格里帕', 'Aquila': '天鹰',
    'Aurum': '黄金', 'Cato': '加图', 'Cæsar': '恺撒', 'Cervus': '牡鹿',
    'Delphinus': '海豚', 'Etna': '埃特纳', 'Ferrum': '玄铁',
    'Gladiator': '角斗士', 'Gloria Imperii': '帝国荣光',
    'Iulius Cæsar': '尤利乌斯·恺撒', 'Leo': '雄狮', 'Lepus': '野兔',
    'Marcus Aurelius': '马可·奥勒留', 'Præda': '战利品', 'Sagitta': '天箭',
    'Scipio': '西庇阿', 'Seneca': '塞内卡', 'Spiculum': '锋矛',
    'Venator': '猎手', 'Vergilius': '维吉尔', 'Vespa': '黄蜂',
    'Vesuvius': '维苏威',
}

NAMES = {**RIVERS, **INCA, **MEANING}

po = 'data/i18n/translations/tribes/zh_CN.po'
entries = [e for e in parse_po(po)
           if not e.is_header and e.ctxt == 'shipname' and not e.translated]

out = {}
missing = []
for e in entries:
    zh = NAMES.get(e.msgid)
    if zh is None:
        missing.append(e.msgid)
        continue
    out[key_of(e)] = zh + '号'

dest = sys.argv[1]
json.dump(out, open(dest, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'译出 {len(out)} / {len(entries)}')
if missing:
    print(f'未覆盖 {len(missing)}：{" ".join(missing)}')
