# -*- coding: utf-8 -*-
import requests
import re
import time
import os
from lxml import etree

import filepath
import logmodule
import doubanurl

logger = logmodule.LogModule()
group_dict = dict()


def get_cookies():
    # 获取豆瓣登录Cookie信息

    cookies = {}
    cookies_file = filepath.cookie_txt
    f_cookie = file(cookies_file, "r")
    douban_cookies = f_cookie.readlines()[0].split("; ")
    for line in douban_cookies:
        key, value = line.split("=", 1)
        cookies[key] = value
    return cookies


def get_active_group_set():
    # 获取所有活跃（人数超过10000）小组的id，存入set中

    active_group_set = set()
    with open(filepath.active_group_id_txt, "r") as f_agit:
        for line in f_agit.readlines():
            group_id = str(line).strip()
            if group_id is not None and group_id is not "" and group_id is not "\n":
                active_group_set.add(group_id)
    return active_group_set


def split_group_url(url):
    # 从小组的url中分割出 小组名称/id

    group = url[29:]
    group = group[:-1]
    return group


def get_group_joins(user_id):
    # 通过用户id获取用户加入的所有小组

    group_joins_id_sets = set()
    group_joins_url = doubanurl.DOUBAN_GROUP + "people/" + str(user_id) + "/joins"
    r = requests.get(group_joins_url, cookies=get_cookies())
    group_joins_html = etree.HTML(r.text)
    group_user_joins_url_array = group_joins_html.xpath(
        "//div[@class='group-list group-cards']//li//div[@class='title']/a/@href")
    for url in group_user_joins_url_array:
        logger.info(url)
        group = split_group_url(url)
        if group.isdigit():
            group_joins_id_sets.add(group)
        else:
            group_joins_id_sets.add(group_name_to_id(group))
    logger.info(group_joins_id_sets)
    time.sleep(1)
    return group_joins_id_sets


def group_name_to_id(group_name):
    # 小组url中，如果非id，进行转换；group_dict缓存已经转换过的

    if group_name in group_dict:
        logger.info("key already exists: " + group_name + "<->" + group_dict[group_name])
        return group_dict[group_name]
    else:
        group_url = doubanurl.DOUBAN_SITE + group_name
        r = requests.get(group_url, cookies=get_cookies())
        if r.status_code == 200:
            group_html = etree.HTML(r.text)
            group_id = group_html.xpath("//form[@action='/group/search']/input[@name='group']/@value")
            logger.info("transform group name to id: " + group_name + "<->" + group_id[0])
            group_dict[group_name] = group_id[0]
            # name<->id 映射写入文件
            with open(filepath.auig_ni_txt, "a+") as f_auig_ni:
                f_auig_ni.write(str(group_name).strip() + "\t" + str(group_id[0]).strip() + "\n")
            time.sleep(1)
            return group_id[0]
        else:
            logger.warning("fail to transform in name_to_id func: " + str(group_url) + " "+ str(r.status_code))
            return group_name


def cache_group_name_id():
    # 如果映射小组name和id的缓存文件存在，先将其读入字典中

    if os.path.exists(filepath.auig_ni_txt):
        with open(filepath.auig_ni_txt, "r") as nameid:
            for line in nameid.readlines():
                g_name = line.split("\t")[0].strip()
                g_id = line.split("\t")[1].strip()
                group_dict[g_name] = g_id


def init_func():
    # 载入缓存的字典
    cache_group_name_id()


def get_verify_code_pic(group_id):
    # 获取验证码的图片URL和id

    topic_new_url = doubanurl.DOUBAN_GROUP + str(group_id) + "/new_topic"
    r = requests.get(topic_new_url, cookies=get_cookies())
    if r.status_code == 200:
        pic_url, pic_id = get_image_and_id(r.text)
        return pic_url, pic_id
    else:
        logger.warning(str(topic_new_url) + ", status_code: " + str(r.status_code))
        return "", ""


def get_image_and_id(text):
    # 通过html提取验证码图片URL和id

    html = etree.HTML(text)
    pic_url = html.xpath("//img[@class='captcha_image']/@src")
    pic_id = html.xpath("//input[@name='captcha-id']/@value")
    if len(pic_url) and len(pic_id):
        return pic_url[0], pic_id[0]
    else:
        return "", ""


def get_form_ck_from_new_post(url):
    # 获取发帖需要的ck，ck值会随着用户的切换而变化，ck值隐藏在发帖的form表单中

    r = requests.get(url, cookies=get_cookies())
    html = etree.HTML(r.text)
    ck = html.xpath("//form[@name='lzform']//input[@name='ck']/@value")
    if len(ck):
        return ck[0]
    else:
        return ""

