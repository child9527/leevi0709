# -*- coding: utf-8 -*-
# !/usr/bin/python
import requests
import base64
import random
import re
import json
import sys
import urllib.parse
import ssl
import urllib3
import hashlib
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

urllib3.disable_warnings()
sys.path.append('..')
from base.spider import Spider


class TLSAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ciphers = (
            'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:'
            'ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:'
            'ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:'
            'DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384'
        )
        context = create_urllib3_context(ciphers=ciphers)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        kwargs['ssl_context'] = context
        return super(TLSAdapter, self).init_poolmanager(*args, **kwargs)


class Spider(Spider):
    def __init__(self):
        super(Spider, self).__init__()
        self.session = requests.Session()
        self.session.verify = False
        self.session.mount('https://', TLSAdapter())
        self.host = "https://www.cd-zj.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
            'Referer': f'{self.host}/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }

    def getName(self):
        return "枫叶4K影院-CDZJ"

    def init(self, extend):
        pass

    def homeContent(self, filter):
        classes = [
            {"type_id": "1", "type_name": "电影"},
            {"type_id": "2", "type_name": "电视剧"},
            {"type_id": "4", "type_name": "动漫"},
            {"type_id": "3", "type_name": "综艺"},
            {"type_id": "5", "type_name": "热门短剧"},
        ]

        filter_dict = {}
        years = [{"n": "全部", "v": ""}] + [{"n": str(y), "v": str(y)} for y in range(2026, 2003, -1)]
        orders = [
            {"n": "按最新", "v": "time"},
            {"n": "按最热", "v": "hits"},
            {"n": "按评分", "v": "score"}
        ]

        movie_classes = ["动作", "喜剧", "爱情", "科幻", "恐怖", "剧情", "战争", "惊悚", "悬疑", "犯罪", "奇幻", "冒险",
                         "动画", "武侠"]
        movie_areas = ["大陆", "香港", "台湾", "美国", "韩国", "日本", "泰国", "新加坡", "马来西亚", "印度", "英国",
                       "法国", "加拿大", "西班牙", "俄罗斯", "其它"]

        tv_classes = ["古装", "战争", "青春偶像", "喜剧", "家庭", "犯罪", "动作", "奇幻", "剧情", "历史", "经典",
                      "乡村", "情景", "商战", "网剧", "其他"]
        tv_areas = ["内地", "韩国", "香港", "台湾", "日本", "美国", "泰国", "英国", "新加坡", "其他"]

        comic_classes = ["科幻", "热血", "推理", "搞笑", "冒险", "萝莉", "校园", "动作", "机战", "运动", "战争", "少年",
                         "少女"]
        show_classes = ["脱口秀", "真人秀", "搞笑", "访谈", "生活", "晚会", "美食", "游戏", "亲子", "旅游", "音乐",
                        "舞蹈"]

        def create_filter(classes_list, areas_list):
            return [
                {"key": "class", "name": "类型",
                 "value": [{"n": "全部", "v": ""}] + [{"n": c, "v": c} for c in classes_list]},
                {"key": "area", "name": "地区",
                 "value": [{"n": "全部", "v": ""}] + [{"n": a, "v": a} for a in areas_list]},
                {"key": "year", "name": "年份", "value": years},
                {"key": "by", "name": "排序", "value": orders}
            ]

        filter_dict["1"] = create_filter(movie_classes, movie_areas)
        filter_dict["2"] = create_filter(tv_classes, tv_areas)
        filter_dict["4"] = create_filter(comic_classes, tv_areas)
        filter_dict["3"] = create_filter(show_classes, tv_areas)
        filter_dict["5"] = create_filter(["女频", "男频", "复仇", "甜宠", "穿越", "逆袭", "战神", "脑洞"],
                                         ["内地", "其他"])

        return {"class": classes, "filters": filter_dict}

    def homeVideoContent(self):
        return {'list': []}

    def categoryContent(self, cid, pg, filter, ext):
        page = int(pg)
        ext = ext or {}
        area = ext.get('area', '')
        by = ext.get('by', '')
        class_name = ext.get('class', '')
        year = ext.get('year', '')

        # cd-zj.com URL格式: /type/{cid}/class/{class}/area/{area}/year/{year}/by/{by}/page/{page}.html
        parts = [f"/type/{cid}"]
        if class_name:
            parts.append(f"class/{urllib.parse.quote(class_name)}")
        if area:
            parts.append(f"area/{urllib.parse.quote(area)}")
        if year:
            parts.append(f"year/{year}")
        if by:
            parts.append(f"by/{by}")
        if page > 1:
            parts.append(f"page/{page}")
        parts.append(".html")

        url = self.host + "/".join(parts[:-1]) + parts[-1]
        res = self.session.get(url, headers=self.headers)
        text = res.text

        videos = []
        # 匹配影片块
        # 图片: <img data-src="{pic}" ...>
        # 备注: <span class="public-list-prb hide"><i class="ft2">{note}</i></span>
        pattern = r'<a[^>]*class="public-list-exp"[^>]*href="/detail/(\d+)\.html"[^>]*title="([^"]*)"[^>]*>.*?<img[^>]*data-src="([^"]*)"[^>]*>.*?<span[^>]*class="public-list-prb[^"]*"[^>]*>.*?>([^<]*)</[^>]*>'
        for m in re.finditer(pattern, text, re.DOTALL):
            vid = m.group(1)
            name = m.group(2).strip()
            pic = m.group(3) if m.group(3) else ''
            note = m.group(4) if m.group(4) else ''
            pic = pic.replace('&amp;', '&')
            videos.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": pic,
                "vod_remarks": note
            })

        return {'list': videos, 'page': page, 'pagecount': 9999, 'limit': 90, 'total': 999999}

    def detailContent(self, ids):
        did = ids[0]
        url = f"{self.host}/detail/{did}.html"
        res = self.session.get(url, headers=self.headers, timeout=10)
        text = res.text

        # 提取标题
        name = ""
        h1_match = re.search(r'<h1[^>]*class="slide-info-title"[^>]*>([^<]+)</h1>', text)
        if not h1_match:
            h1_match = re.search(r'<h3[^>]*class="slide-info-title[^"]*"[^>]*>([^<]+)</h3>', text)
        if h1_match:
            name = h1_match.group(1).strip()

        # 提取slide-info信息
        actor, director, year, content, state = "", "", "", "", ""
        info_pattern = r'<div[^>]*class="slide-info hide"[^>]*>(.*?)</div>'
        info_blocks = re.findall(info_pattern, text, re.DOTALL)
        for block in info_blocks:
            clean = re.sub(r'<[^>]+>', '', block).strip()
            if '演员：' in clean or '主演：' in clean:
                actor = clean.replace('演员：', '').replace('主演：', '').strip()
            elif '导演：' in clean:
                director = clean.replace('导演：', '').strip()
            elif '年份：' in clean or '上映：' in clean:
                year = clean.replace('年份：', '').replace('上映：', '').strip()
            elif '更新' in clean or '连载' in clean:
                state = clean
            elif '类型：' in clean:
                pass  # 类型不需要单独字段

        # 提取简介
        desc_match = re.search(r'id="height_limit"[^>]*class="text cor3"[^>]*>(.*?)</div>', text, re.DOTALL)
        if desc_match:
            content = re.sub(r'<[^>]+>', '', desc_match.group(1)).strip()
        else:
            # 备用: 找包含简介关键词的文本
            desc_match2 = re.search(r'简介[：:]\s*([^<]+)', text)
            if desc_match2:
                content = desc_match2.group(1).strip()

        # 提取播放源和集数
        play_from, play_url = [], []

        # 从集数链接提取: /play/{id}-{sid}-{nid}.html
        ep_pattern = r'href="/play/(\d+)-(\d+)-(\d+)\.html"[^>]*>([^<]+)</a>'
        eps = re.findall(ep_pattern, text)

        # 按源分组
        sources_map = {}
        for vid, sid, nid, ep_name in eps:
            if sid not in sources_map:
                sources_map[sid] = []
            ep_url = f"{self.host}/play/{vid}-{sid}-{nid}.html"
            sources_map[sid].append(f"{ep_name.strip()}${ep_url}")

        # 按sid排序
        for sid in sorted(sources_map.keys(), key=int):
            ep_list = sources_map[sid]
            ep_list.reverse()  # 正序排列
            play_from.append(f"多多线路{sid}")
            play_url.append('#'.join(ep_list))

        return {'list': [{
            "vod_id": did,
            "vod_name": name,
            "vod_actor": actor,
            "vod_director": director,
            "vod_content": content,
            "vod_remarks": state,
            "vod_year": year,
            "vod_play_from": '$$$'.join(play_from),
            "vod_play_url": '$$$'.join(play_url)
        }]}

    def playerContent(self, flag, id, vipFlags):
        try:
            res = self.session.get(id, headers=self.headers, timeout=5)
            match = re.search(r'var\s+player_aaaa\s*=\s*(\{[\s\S]*?\})\s*</script>', res.text)
            if not match:
                return {'parse': 0, 'url': ''}

            player_data = json.loads(match.group(1))
            durl = player_data.get('url', '')
            encrypt = player_data.get('encrypt', 0)
            from_flag = player_data.get('from', '')

            if encrypt == 1:
                durl = urllib.parse.unquote(durl)
            elif encrypt == 2:
                durl = urllib.parse.unquote(durl)
                durl = base64.b64decode(durl).decode('utf-8')
                durl = urllib.parse.unquote(durl)

            # cd-zj.com encrypt=0, url直接是密文(如JD-xxx)，需要走解析流程
            if durl.startswith('http') and ('.m3u8' in durl or '.mp4' in durl):
                return {'parse': 0, 'url': durl}

            # 获取解析接口
            config_url = f"{self.host}/static/js/playerconfig.js"
            config_res = self.session.get(config_url, headers=self.headers, verify=False, timeout=5)

            parse_api = ""
            if from_flag:
                m = re.search(f'"{from_flag}":\\{{[^}}]*"parse":"([^"]+)"', config_res.text)
                if m:
                    parse_api = m.group(1).replace('\\/', '/')
            if not parse_api:
                m = re.search(r'"parse":"(http[^"]+)"', config_res.text)
                if m:
                    parse_api = m.group(1).replace('\\/', '/')
            if not parse_api:
                parse_api = "https://fgsrg.hzqingshan.com/player/?url="

            iframe_url = parse_api + durl
            print(f"[*] iframe解析: {iframe_url}")

            iframe_headers = self.headers.copy()
            iframe_headers['Referer'] = id
            iframe_res = self.session.get(iframe_url, headers=iframe_headers, verify=False, timeout=5)

            iframe_soup_text = iframe_res.text
            player_data_tag = re.search(r'id="player-data"[^>]*data-te="([^"]*)"[^>]*data-bt="([^"]*)"', iframe_soup_text)

            if not player_data_tag:
                return {'parse': 1, 'url': iframe_url}

            token = player_data_tag.group(1)
            bt = player_data_tag.group(2)

            api_base = urllib.parse.urlparse(parse_api)
            api_host = f"{api_base.scheme}://{api_base.netloc}"
            api_url = f"{api_host}{bt}mplayer.php"

            post_data = {'url': durl, 'token': token}

            api_headers = self.headers.copy()
            api_headers['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8'
            api_headers['X-Requested-With'] = 'XMLHttpRequest'
            api_headers['Referer'] = iframe_url
            api_headers['Origin'] = api_host

            api_res = self.session.post(api_url, data=post_data, headers=api_headers, verify=False, timeout=10)

            if api_res.status_code == 200:
                try:
                    api_json = api_res.json()
                except:
                    return {'parse': 1, 'url': iframe_url}

                print(f"[*] API响应: {api_json}")

                real_url = api_json.get('url') or api_json.get('data', {}).get('url', '')
                urlmode = str(api_json.get('urlmode') or api_json.get('data', {}).get('urlmode', ''))

                # cd-zj.com 实测urlmode为空，直接返回真实m3u8
                if urlmode == '1':
                    real_url = self.js_decrypt1(real_url)
                elif urlmode == '2':
                    real_url = self.js_decrypt2(real_url)
                elif urlmode == '3':
                    real_url = self.js_decrypt3(real_url)

                # 多次尝试decrypt3
                for _ in range(3):
                    if real_url and real_url.startswith('WyJ') and '/' in real_url:
                        real_url = self.js_decrypt3(real_url)
                    else:
                        break

                if real_url:
                    print(f"[*] 最终URL: {real_url}")
                    return {'parse': 0 if ('.m3u8' in real_url or '.mp4' in real_url) else 1, 'url': real_url}

            return {'parse': 1, 'url': iframe_url}

        except Exception as e:
            print(f"[*] 播放解析错误: {e}")
            return {'parse': 1, 'url': id}

    def searchContent(self, key, quick, pg="1"):
        # cd-zj.com 使用ajax suggest接口搜索
        suggest_url = f'{self.host}/index.php/ajax/suggest'
        try:
            res = self.session.get(suggest_url, params={'mid': '1', 'wd': key}, headers=self.headers, timeout=10)
            data = res.json()

            videos = []
            if data.get('code') == 1 and data.get('list'):
                for item in data.get('list', []):
                    videos.append({
                        "vod_id": str(item.get('id', '')),
                        "vod_name": item.get('name', ''),
                        "vod_pic": item.get('pic', '').replace('&amp;', '&'),
                        "vod_remarks": ""
                    })

            return {'list': videos, 'page': int(pg), 'pagecount': 1, 'limit': len(videos), 'total': len(videos)}
        except Exception as e:
            print(f"[*] 搜索错误: {e}")
            return {'list': [], 'page': int(pg), 'pagecount': 1, 'limit': 0, 'total': 0}

    def js_decrypt1(self, data):
        try:
            key = hashlib.md5(b'test').hexdigest()
            dec1 = base64.b64decode(data)
            code = bytearray([dec1[i] ^ ord(key[i % len(key)]) for i in range(len(dec1))])
            return base64.b64decode(code).decode('utf-8')
        except:
            return data

    def js_decrypt2(self, data):
        staticchars = "PXhw7UT1B0a9kQDKZsjIASmOezxYG4CHo5Jyfg2b8FLpEvRr3WtVnlqMidu6cN"
        try:
            dec = base64.b64decode(data).decode('utf-8', errors='ignore')
            return "".join(
                [staticchars[(staticchars.find(dec[i]) + 59) % 62] if staticchars.find(dec[i]) != -1 else dec[i] for i
                 in range(1, len(dec), 3)])
        except:
            return data

    def js_decrypt3(self, data):
        def fix_b64(s):
            return s + '=' * (4 - len(s) % 4) if len(s) % 4 else s

        try:
            parts = data.split('/')
            if len(parts) >= 3:
                arr1 = json.loads(base64.b64decode(fix_b64(parts[0])).decode('utf-8'))
                arr2 = json.loads(base64.b64decode(fix_b64(parts[1])).decode('utf-8'))
                cipher = base64.b64decode(fix_b64('/'.join(parts[2:]))).decode('utf-8', errors='ignore')
                return "".join([arr1[arr2.index(c)] if c in arr2 else c for c in cipher])
        except:
            pass
        return data