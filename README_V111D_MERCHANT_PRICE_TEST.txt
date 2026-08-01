MMMerge Korean v1.0.11d - Merchant Price Text Test

Fixes the regular-Merchant purchase description when the actual purchase
price is higher than the displayed base price.

Old wording:
  Claims the player negotiated well, even when the final price is higher.

New wording:
  %24의 기준 가격은 %25골드이며, 현재 구매 가격은 %27골드입니다.

Token contract:
  %24 = item name
  %25 = base/reference price
  %27 = final price actually charged

Test:
  Hover an item in a shop while using regular Merchant skill. Confirm that the
  first number is labeled as the base price, the second number is labeled as
  the current purchase price, and buying deducts the second number.
