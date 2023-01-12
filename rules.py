D4 = [1,2,3,4]
D6 = [1,2,3,4,5,6]
D8 = [1,2,3,4,5,6,7,8]
D10 = [1,2,3,4,5,6,7,8,9,10]
D12 = [1,2,3,4,5,6,7,8,9,10,11,12]
D20 = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20]

    

def diceSelector(dice):
    match dice:
        case 4:
            return D4
        case 6:
            return D6
        case 8:
            return D8
        case 10:
            return D10
        case 12:
            return D12
        case 20:
            return D20
        case _:
            False