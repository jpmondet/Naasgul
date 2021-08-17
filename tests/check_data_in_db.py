"""Quick&Dirty something to get/check data stored in mongodb"""
# /usr/bin/env python3


from pymongo import MongoClient  # type: ignore

# https://pymongo.readthedocs.io/en/stable/tutorial.html

AUTOMAPPING_DB: str = "mongodb://localhost:27017/"

client = MongoClient(AUTOMAPPING_DB)

db = client.automapping

# print("\n\n\n\INDEX")
# print(list(db.index_seq.find()))
# print("\n\n\n\nNODES")
# print(list(db.nodes.find()))
# print("\n\n\n\nLINKS")
# print(list(db.links.find()))
# print("\n\n\n\nSTATS")
# print(list(db.stats.find()))
# print("\n\n\n\nUTILIZATION")
# print(list(db.utilization.find()))


# db.nodes.delete_many({})
# db.links.delete_many({})
# db.stats.delete_many({})
# db.utilization.delete_many({})

print("\n\n\n\nNODES")
# print(db.nodes.find_one({"device_name": "test_static1"}))
for node in db.nodes.find():
    print(node)
# print("\n\n\n\nLINKS")
# print(list(db.links.find(
# {'device_name': 'fake_device_stage8_13', 'neighbor_name': "test_static_device"})))
# print(list(db.links.find({'device_name': 'test_static'})))
# print(list(db.links.find({'device_name': 'test1'})))
# print(list(db.links.find({'neighbor_name': 'test_static'})))
# for link in db.links.find():
#    print(link)
print("\n\n\n\nSTATS")
# print(list(db.stats.find({'device_name': 'fake_device_stage1_1', 'iface_name': '1/1'})))
for stat in db.stats.find():
    print(stat)
print("\n\n\n\nUTILIZATION")
for utilization in db.utilization.find():
    print(utilization)
# print(list(db.links.find({'device_name': 'fake_device_stage6_16', 'iface_name': '0/16'})))
# l = list(db.stats.find({'device_name': 'fake_device_stage6_16', 'iface_name': '0/16'}))
# l = list(db.stats.find({"device_name": "rtr3.iou", "iface_name": "0/0"}))
# print(l)
# print(l[-1])
