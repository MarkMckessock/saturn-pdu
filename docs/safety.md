# Safety

Read this before building and before operating. It is written in plain terms
deliberately -- nothing here requires an electronics background.

---

## 1. The two hazards, separated

People conflate these, and they need different responses.

| | Mains side (inside the chassis) | DC side (19V outputs) |
|---|---|---|
| Voltage | 100-240V AC | 19V DC |
| Shock hazard | **Yes. Can kill you.** | **No.** Below every threshold that matters |
| Short-circuit hazard | Yes, plus arc flash | Yes -- burns, melted parts, ignition risk |
| Applies to | IEC inlet, PSU input terminals | Barrel jacks, interconnect cables |

**19V DC cannot shock you.** IEC 62368-1 classes DC below 60V as **ES1** -- no
electrical energy hazard under normal conditions. You can touch a live 19V
barrel plug with dry hands and feel nothing. This is why the outputs are safe to
handle while energised and the mains side is not.

---

## 2. Live barrel plugs

**The concern:** the interconnect cables have a barrel plug at both ends. If a
cable is plugged into the PDU but not into a node, its free end is a live 19V
male plug with exposed tip and sleeve about a millimetre apart.

**What is and is not at risk:**

- **You are not at risk.** See ES1 above.
- **The rack is.** Drop that plug on a rail, a screw or a bare cable shield and
  you bridge 19V through a source that delivers up to 10.5A before the channel's
  current limit engages. Roughly 200W into a contact the size of a pinhead.
  Expect sparks, a melted plug, a scorch mark, and the plug possibly welding
  itself to whatever it touched.

**Important context: this hazard is not new.** Every stock Huntkey brick has a
captive cable ending in a male plug, live at 19V with 9.47A behind it whenever
the brick is in the wall. Six bricks means six of these already in your rack
today. The PDU inherits the hazard; it does not create it.

**And it inherits it with an advantage the bricks do not have:** a dangling
cable can be de-energised remotely, from anywhere. With a brick the only option
is pulling it out of the wall.

### How this design responds

| Control | What it does |
|---|---|
| **Unconnected-output alert** (P-12) | A port that is enabled at 19V but drawing under 20mA has nothing on it. The INA226s already measure this. Raises an alarm on the display, in the logs and in `/metrics` |
| **Alert only -- never an automatic switch-off** | A faulty shunt reading must never be able to de-energise a running node. A false positive here is annoying; the alternative is an outage |
| **Operating procedure** (below) | The control that actually does the work |

> **Locking plugs were considered and dropped.** An earlier draft specified a
> threaded-collar locking jack at the PDU end to prevent the accidental
> disconnection that creates a dangling live plug. It was removed for two
> reasons. First, **no such part exists** at an adequate current rating: the
> 5.5 x 2.5mm format tops out around 5-8A industry-wide, and every locking
> variant is 5A -- below what a channel delivers (WP-3 sourcing). Second, and
> more to the point, it was solving a problem the stock bricks already have and
> nobody loses sleep over.
>
> **The honest consequence: the P-12 alert and the operating procedure below are
> now the whole of the response.** That is a thinner set of controls than the
> earlier draft claimed, and it is stated plainly rather than quietly dropped.
> It is judged acceptable because the hazard is ES1 to a person, is inherited
> rather than introduced, and -- unlike with a brick -- can be switched off from
> anywhere.

### Operating procedure

1. **Unused ports stay off.** If nothing is plugged into port 4, port 4 is off.
2. **Switch a port off before unplugging it.** Both ends, every time.
3. **Never leave a cable connected at the PDU end only.** If a node comes out of
   the rack, the cable comes out of the PDU.
4. The rear panel is labelled with rules 1-3. It is not a substitute for them.

---

## 3. Mains side

This is the part that can actually hurt you.

- **No user-accessible mains voltage with the lid fitted** (requirement P-11).
  The IEC inlet, its fuse and the PSU's AC terminals are inside the chassis.
- **Unplug at the wall before opening the lid.** The PSU's remote ON/OFF turns
  the *output* off. It does not isolate the mains input. An "off" PDU still has
  240V on its input terminals.
- **Wait 60 seconds after unplugging** before touching anything inside. The
  PSU's input capacitors hold charge.
- AC wiring inside the chassis uses insulated, strain-relieved terminations with
  no exposed conductor. Heat-shrink every AC crimp.

---

## 4. Bench work

The bring-up programme in `docs/SPECIFICATION.md` section 9 exists because this
design has had **no independent review** -- a deliberate decision, recorded as
risk R-0. The bench tests are what stands in for that review. The rules:

1. **Power bring-up from a current-limited bench supply, never the RSP-750.**
   A 750W supply will pour everything it has into a mistake. A bench supply set
   to 1A will not.
2. **Never bench-test into an MS-01.** Use a resistive dummy load. Bring-up
   failures are expected, and they should cost $30, not $700.
3. **The destructive OVP test is mandatory and must be performed, not reasoned
   about.** Deliberately short a high-side FET drain-to-source and confirm the
   crowbar protects a dummy load. This is the exact failure mode that destroys
   nodes. Sacrifice the FET.
4. **Run the full fault set twice** -- once on a fresh board, once after the
   72-hour burn-in. Protection that works cold and fails on a thermally-aged
   board is precisely what the canary stage exists to catch, and catching it
   here is far cheaper.
5. **The 30-day canary is a hard gate.** One worker node, never a control-plane
   node. Any protection event, any thermal drift, any unexplained reboot resets
   the clock to day zero and the cause must be *found*, not merely monitored.

---

## 5. What this design does not protect against

Stated plainly so it is not assumed.

- **A design error common to all six channels.** The protection is per-channel
  and independent, but if the *design* of that protection is wrong it is wrong
  six times. This is the residual of R-0 and it is why the canary is 30 days on
  one node rather than a weekend on six.
- **Mains-side faults upstream of the IEC inlet.** That is your building's
  breaker, not this box.
- **Loss of the whole PDU.** There is no output redundancy -- that was analysed
  and explicitly rejected (SPECIFICATION section 4.2.4). A PSU failure, a
  backplane fault or a blown bus fuse takes all six nodes down. If the cluster
  must survive that, the answer is a second PDU, not a bigger one.
