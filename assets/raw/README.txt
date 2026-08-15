Drop RAW phone screenshots here (straight off the phone, any size).

They are turned into store cards by tools/make_card.py, which puts them on
the same background and type as your existing eight cards. Nothing is drawn:
the gradient is learned from your own artwork, the phone is your screenshot.

  python tools/make_card.py assets/raw/sounds.png \
      "Send a sound, not a smiley" "22 effects mapped to real emoji" pulsesoul_20
  python tools/render_images.py

Keep the demo family (Papa, Mummy, Didi) in shot. No real numbers or faces.
