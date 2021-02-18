import json
from peewee import *
import requests
from datetime import datetime

apiBaseUrl = 'https://api.agefans.app/v2/detail/'
detailBaseUrl = 'https://www.agefans.net/detail/'
db = SqliteDatabase('data.db')


class BaseModel(Model):
    class Meta:
        database = db


class AniInfo(BaseModel):
    aid = CharField(primary_key=True)
    oriName = CharField(null=True)
    cnName = CharField(null=True)
    otherName = CharField(null=True)
    status = CharField(null=True)
    tags = CharField(null=True)
    latestEpisode = TextField(null=True)
    detailUrl = CharField(null=True)
    premiereTime = DateField(null=True)
    updateTime = DateTimeField(null=True)
    picUrl = CharField(null=True)

    def __repr__(self):
        # markdown 格式
        res = ''
        for item in self.__data__:
            if item == 'latestEpisode':
                res += '**latestEpisode:**\n\n```json\n' + self.latestEpisode + '\n```\n\n'
            elif item == 'detailUrl':
                res += '**detailUrl:** [%s](%s)\n\n' % (self.cnName, detailBaseUrl + self.aid)
            else:
                res += '**%s:** %s\n\n' % (item, str(getattr(self, item)).replace('\n', '\n\n'))
        return res

    def __str__(self):
        return self.__repr__()


def getInfoFromDetailJson(detail):
    info = detail['AniInfo']
    aniInfo = AniInfo()
    aniInfo.aid = info['AID']
    aniInfo.oriName = info['R原版名称']
    aniInfo.cnName = info['R动画名称']
    aniInfo.otherName = info['R其它名称']
    aniInfo.status = info['R播放状态']
    aniInfo.tags = info['R剧情类型']
    aniInfo.detailUrl = detailBaseUrl + aniInfo.aid
    aniInfo.premiereTime = datetime.strptime(info['R首播时间'], '%Y-%m-%d')
    aniInfo.updateTime = datetime.fromtimestamp(info['R更新时间unix'])
    aniInfo.latestEpisode = json.dumps(detail['AniPreRel'], ensure_ascii=False,
                                       indent=2, sort_keys=True)
    if detail.get('AniPreRel'):
        aniInfo.picUrl = '![](%s)' % detail['AniPreRel'][0]['PicSmall']
    else:
        aniInfo.picUrl = '![](%s)' % info['R封面图']
    return aniInfo


def getAniInfoFromDb(aid):
    try:
        return AniInfo.select().where(AniInfo.aid == aid).get()
    except:
        return None


def getAniInfoFromApi(aid):
    response = requests.get(apiBaseUrl + aid)
    return getInfoFromDetailJson(response.json())


def checkIfNeedToFireNotify(oldInfo: AniInfo, newInfo: AniInfo):
    if oldInfo is None:
        return True
    return oldInfo.updateTime != newInfo.updateTime


def sendToWechat(sckey, title, content):
    url = 'https://sc.ftqq.com/' + sckey + '.send'
    data = {'text': title, 'desp': content}
    result = requests.post(url, data)
    return result


def sendBySct(sckey, title, content):
    url = 'https://sctapi.ftqq.com/' + sckey + '.send'
    data = {'text': title, 'desp': content}
    result = requests.post(url, data)
    return result


def sendByTgBot(chatId, title, content):
    # @shadowfox_MsgCat_bot
    result = requests.post('https://msgcat.shadowfox.workers.dev/',
                           json={'chatId': chatId, 'title': title, 'content': content})
    return result


def readConfig():
    with open('./config.json', 'r') as f:
        return json.load(f)


def main():
    config = readConfig()
    for aid in config['aids']:
        print('checking aid:', aid)
        oldInfo = getAniInfoFromDb(aid)
        if oldInfo and oldInfo.status != '连载':
            print('%s 已经 %s 了, 跳过' % (oldInfo.cnName, oldInfo.status))
            continue
        newInfo = getAniInfoFromApi(aid)
        if checkIfNeedToFireNotify(oldInfo, newInfo):
        # if True:
            title = newInfo.cnName + ' 更新了'
            print(title)
            sendByTgBot(config['tg-chat-id'], title, str(newInfo))
            AniInfo.insert(newInfo.__data__).on_conflict_replace().execute()


if __name__ == '__main__':
    AniInfo.create_table()
    main()
