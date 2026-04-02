list1 = [i for i in range(64)]
print(f"原列表长度: {len(list1)}")  # 64

n = len(list1)
start_index = -n // 4  # -16
end_index = 3 * n // 4  # 48

# 修正切片范围：去掉 [-1]，改为取到末尾
list2 = list1[start_index:].copy()  # 等价于 list1[48:64]，包含索引63
list2.extend(list1[:end_index])     # 扩展 list1[0:48]
list2 = list2[::-1]  # 确保列表长度为64
print(f"合并后列表长度: {len(list2)}")  # 16 + 48 = 64
print(list2)